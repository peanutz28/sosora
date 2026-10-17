"""Bounded development-only supervised architecture comparison; never opens final labels."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F


class UNet(nn.Module):
    """Randomly initialized compact U-Net; not a pretrained general-purpose model."""
    def __init__(self, width=16):
        super().__init__()
        def block(a, b):
            return nn.Sequential(nn.Conv2d(a,b,3,padding=1), nn.ReLU(), nn.Conv2d(b,b,3,padding=1), nn.ReLU())
        self.e1=block(3,width); self.e2=block(width,width*2)
        self.e3=block(width*2,width*4); self.e4=block(width*4,width*8)
        self.middle=block(width*8,width*16)
        self.d4=block(width*24,width*8); self.d3=block(width*12,width*4)
        self.d2=block(width*6,width*2); self.d1=block(width*3,width)
        self.head=nn.Conv2d(width,2,1)
    def forward(self,x):
        a=self.e1(x); b=self.e2(F.max_pool2d(a,2))
        c=self.e3(F.max_pool2d(b,2)); d=self.e4(F.max_pool2d(c,2))
        z=self.middle(F.max_pool2d(d,2))
        z=self.d4(torch.cat([F.interpolate(z,size=d.shape[-2:],mode='bilinear',align_corners=False),d],1))
        z=self.d3(torch.cat([F.interpolate(z,size=c.shape[-2:],mode='bilinear',align_corners=False),c],1))
        z=self.d2(torch.cat([F.interpolate(z,size=b.shape[-2:],mode='bilinear',align_corners=False),b],1))
        return self.head(self.d1(torch.cat([F.interpolate(z,size=a.shape[-2:],mode='bilinear',align_corners=False),a],1)))



def validate_manifest(rows):
    groups={}; paths={}
    if not rows: raise ValueError('Empty manifest')
    for row in rows:
        split=row['split']
        if split not in {'train','validation'}:
            raise ValueError('Development runner rejects final/test rows before opening files')
        group=row['spatial_group']
        if group in groups and groups[group]!=split: raise ValueError('Spatial group leakage')
        groups[group]=split
        for key in ('image','mask'):
            path=str(Path(row[key]).resolve())
            if path in paths and paths[path]!=split: raise ValueError('File leakage')
            paths[path]=split
    if set(groups.values())!={'train','validation'}: raise ValueError('Need train and validation')


def require_quality_review(manifest, benchmark):
    readiness = Path(manifest).parent/'readiness.json'
    if not benchmark and readiness.exists():
        review=json.loads(readiness.read_text())
        if review.get('status') != 'manual_quality_review_completed':
            raise ValueError('Full training requires completed train/dev quality review')
        if review.get('approved_manifest_sha256') and hashlib.sha256(Path(manifest).read_bytes()).hexdigest()!=review['approved_manifest_sha256']:
            raise ValueError('Manifest does not match the approved quality review')


def sample(row):
    with Image.open(row['image']) as im: image=np.asarray(im.convert('RGB')).copy()
    with Image.open(row['mask']) as im: mask=np.asarray(im).copy()
    if image.shape != (256,256,3) or mask.shape != (256,256): raise ValueError('Need native 256px RGB crops and masks; no resizing')
    if not np.isin(mask,[0,1,255]).all() or not np.any(mask!=255): raise ValueError('Invalid/entirely ignored mask')
    image=torch.from_numpy(image).permute(2,0,1).float()/255
    image=(image-torch.tensor([.485,.456,.406])[:,None,None])/torch.tensor([.229,.224,.225])[:,None,None]
    return image,torch.from_numpy(mask.astype(np.int64))


def logits(model,x):
    out=model(x)
    out=out if isinstance(out,torch.Tensor) else out.logits
    return F.interpolate(out,size=x.shape[-2:],mode='bilinear',align_corners=False)


def make_model(architecture,base):
    if architecture=='unet': return UNet()
    from transformers import SegformerForSemanticSegmentation
    model=SegformerForSemanticSegmentation.from_pretrained(base,local_files_only=True)
    if model.config.num_labels!=2: raise ValueError('Need saved binary initialization checkpoint')
    return model


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True); p.add_argument('--output',required=True)
    p.add_argument('--architecture',choices=['unet','segformer'],required=True)
    p.add_argument('--base',default='ml/artifacts/sn8_native_cpu_v2/baseline_model')
    p.add_argument('--device',choices=['cpu','cuda'],required=True)
    p.add_argument('--threads',type=int,default=2); p.add_argument('--batch-size',type=int,default=4)
    p.add_argument('--seed',type=int,default=42); p.add_argument('--epochs',type=int,default=20)
    p.add_argument('--max-steps',type=int,default=1000); p.add_argument('--max-seconds',type=float,default=3600)
    p.add_argument('--learning-rate',type=float,default=5e-5)
    p.add_argument('--benchmark',action='store_true'); p.add_argument('--warmup',type=int,default=3)
    a=p.parse_args()
    if min(a.threads,a.batch_size,a.epochs,a.max_steps)<1 or a.warmup<0 or not math.isfinite(a.max_seconds) or a.max_seconds<=0 or not math.isfinite(a.learning_rate) or a.learning_rate<=0: raise ValueError('Invalid budget/settings')
    rows=json.loads(Path(a.manifest).read_text()); validate_manifest(rows)
    require_quality_review(a.manifest,a.benchmark)
    out=Path(a.output)
    if out.exists() and any(out.iterdir()): raise ValueError('Refusing output overwrite')
    out.mkdir(parents=True,exist_ok=True)
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.set_num_threads(a.threads)
    model=make_model(a.architecture,a.base).to(a.device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=a.learning_rate)
    train=[r for r in rows if r['split']=='train']; val=[r for r in rows if r['split']=='validation']
    started=time.monotonic(); steps=0; best=-math.inf; selected=None; history=[]; times=[]
    def batch(group):
        samples=[sample(r) for r in group]
        return tuple(torch.stack([s[i] for s in samples]).to(a.device) for i in (0,1))
    def sync():
        if a.device=='cuda': torch.cuda.synchronize()
    for epoch in range(a.epochs):
        random.shuffle(train); model.train()
        for offset in range(0,len(train),a.batch_size):
            if steps>=a.max_steps or time.monotonic()-started>=a.max_seconds: break
            x,y=batch(train[offset:offset+a.batch_size]); sync(); t=time.monotonic()
            optimizer.zero_grad(); loss=F.cross_entropy(logits(model,x),y,ignore_index=255)
            if not torch.isfinite(loss): raise ValueError('Nonfinite loss')
            loss.backward(); optimizer.step(); sync(); steps+=1
            if steps>a.warmup: times.append(time.monotonic()-t)
        if a.benchmark:
            if steps>=a.max_steps or time.monotonic()-started>=a.max_seconds: break
            continue
        model.eval(); tp=fp=fn=tn=0; complete=True
        with torch.inference_mode():
            for row in val:
                if time.monotonic()-started>=a.max_seconds: complete=False; break
                x,y=batch([row]); pred=logits(model,x).argmax(1); valid=y!=255
                tp+=int(((pred==1)&(y==1)&valid).sum()); fp+=int(((pred==1)&(y==0)&valid).sum())
                fn+=int(((pred==0)&(y==1)&valid).sum()); tn+=int(((pred==0)&(y==0)&valid).sum())
        score=2*tp/(2*tp+fp+fn) if complete and 2*tp+fp+fn else None
        history.append(dict(epoch=epoch+1,steps=steps,complete=complete,tp=tp,fp=fp,fn=fn,tn=tn,f1=score))
        if score is not None and score>best:
            best=score; selected=epoch+1
            torch.save({k:v.detach().cpu() for k,v in model.state_dict().items()},out/'best.pt')
        if steps>=a.max_steps or time.monotonic()-started>=a.max_seconds: break
    result=dict(manifest_sha256=hashlib.sha256(Path(a.manifest).read_bytes()).hexdigest(),settings=vars(a),parameters=sum(v.numel() for v in model.parameters()),steps=steps,elapsed_seconds=time.monotonic()-started,measured_steps=len(times),mean_step_seconds=sum(times)/len(times) if times else None,selected_epoch=selected,history=history,role='supervised architecture comparator; development only; no final evaluation',budget_scope='checked between batches; model setup excluded')
    result['checkpoint_sha256']=hashlib.sha256((out/'best.pt').read_bytes()).hexdigest() if (out/'best.pt').exists() else None
    result['runner_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'run.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result))
    if not a.benchmark and selected is None: raise ValueError('No complete finite validation; no selected checkpoint')

if __name__=='__main__': main()
