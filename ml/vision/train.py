"""Binary flood-road fine-tuning using a curated, spatially separated manifest.

Rows: {image, mask, split: train|validation|test, spatial_group}.
Masks: 0=not flooded road, 1=flooded road, 255=unknown.
Unknown flooding attributes must be ignored, never converted to negatives.
"""
import argparse
import json
import math
import uuid
import random
import time
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor
from ml.vision.evaluate import binary_metrics
from ml.vision.provenance import DEFAULT_MODEL, DEFAULT_REVISION, FLOOD_TASK, checkpoint_identity


def prepare_output(path):
    """Never overwrite an existing training run or its evidence."""
    out = Path(path)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("Output must be a new or empty directory")
    out.mkdir(parents=True, exist_ok=True)
    return out


def improved_validation_score(metrics, best_score):
    """Undefined/nonfinite F1 cannot select a checkpoint; ties keep the first."""
    score = metrics.get("f1")
    return isinstance(score, (int, float)) and math.isfinite(score) and score > best_score


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--epochs',type=int,default=3)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--device',choices=['cpu','auto'],default='auto')
    parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--learning-rate',type=float,default=5e-5)
    parser.add_argument('--batch-size',type=int,default=1)
    parser.add_argument('--freeze-backbone',action='store_true')
    parser.add_argument('--max-seconds',type=float)
    parser.add_argument('--skip-test',action='store_true')
    parser.add_argument('--native-tile-inference',action='store_true')
    parser.add_argument('--save-baseline-model',action='store_true')
    args=parser.parse_args()
    if args.threads < 1 or args.batch_size < 1:
        raise ValueError('threads and batch-size must be positive')
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        raise ValueError('learning-rate must be finite and positive')
    if args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0):
        raise ValueError('max-seconds must be finite and positive')
    torch.set_num_threads(args.threads)
    if args.epochs < 1:
        raise ValueError("epochs must be positive")
    out = prepare_output(args.output)
    run_id = str(uuid.uuid4())
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    rows=json.loads(Path(args.manifest).read_text())
    seen={}
    for row in rows:
        group=row['spatial_group']; split=row['split']
        if split not in {'train','validation','test'}:
            raise ValueError('Unknown split')
        if group in seen and seen[group]!=split:
            raise ValueError('Spatial group leakage')
        seen[group]=split
    if not all(any(r['split']==s for r in rows) for s in ['train','validation','test']):
        raise ValueError('Need disjoint train, validation, and test sets')
    device='cpu' if args.device == 'cpu' else ('cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu'))
    processor=SegformerImageProcessor(size={'height':256,'width':256}, do_reduce_labels=False)
    model=SegformerForSemanticSegmentation.from_pretrained(DEFAULT_MODEL, revision=DEFAULT_REVISION, num_labels=2,id2label={0:'non_flooded_road',1:'flooded_road'},label2id={'non_flooded_road':0,'flooded_road':1},ignore_mismatched_sizes=True).to(device)
    if args.native_tile_inference:
        model.config.sosora_tile_size=256
        model.config.requires_road_roi=True
    if args.freeze_backbone:
        for parameter in model.segformer.parameters():
            parameter.requires_grad_(False)
    started=time.monotonic()
    def expired():
        return args.max_seconds is not None and time.monotonic()-started >= args.max_seconds
    def sample(row):
        image=Image.open(row['image']).convert('RGB')
        mask=np.asarray(Image.open(row['mask']))
        if not np.isin(mask,[0,1,255]).all():
            raise ValueError('Mask contains unsupported classes')
        if not np.any(mask!=255):
            raise ValueError('Entirely ignored mask')
        return {k:v.to(device) for k,v in processor(images=image,segmentation_maps=mask,return_tensors='pt').items()}
    def batch_sample(group):
        samples=[sample(row) for row in group]
        return {key:torch.cat([item[key] for item in samples],dim=0) for key in samples[0]}
    def evaluate(split):
        model.eval(); counts={'tp':0,'fp':0,'fn':0,'valid_pixels':0}
        losses=[]
        with torch.inference_mode():
            for row in rows:
                if row['split']!=split: continue
                if expired():
                    return None
                batch=sample(row)
                output=model(**batch)
                losses.append(float(output.loss.detach().cpu()))
                logits=torch.nn.functional.interpolate(output.logits,size=batch['labels'].shape[-2:],mode='bilinear',align_corners=False)
                result=binary_metrics(logits.argmax(1).cpu().numpy(),batch['labels'].cpu().numpy())
                for k in counts: counts[k]+=result[k]
        tp,fp,fn=counts['tp'],counts['fp'],counts['fn']
        counts.update({k:(a/b if b else None) for k,a,b in [('iou',tp,tp+fp+fn),('precision',tp,tp+fp),('recall',tp,tp+fn),('f1',2*tp,2*tp+fp+fn)]})
        counts["loss"] = sum(losses)/len(losses) if losses else None
        return counts
    baseline=evaluate('validation')
    (out/'baseline_validation_metrics.json').write_text(json.dumps({'initialization':'pretrained backbone, randomly initialized binary head; not a general-purpose flood baseline','split':'validation','metrics':baseline},indent=2))
    (out/'baseline_metrics.json').write_text(json.dumps({'initialization':'pretrained backbone, randomly initialized binary head; not a general-purpose flood baseline','status':'not_evaluated_on_test','metrics':None,'split':'validation','validation_metrics':baseline},indent=2))
    if args.save_baseline_model:
        model.save_pretrained(out/'baseline_model')
        processor.save_pretrained(out/'baseline_model')
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=args.learning_rate)
    history=[]
    best_score=-math.inf
    best_state=None
    selected_epoch=None
    stopped_for_time=False
    baseline_state={key:value.detach().cpu().clone() for key,value in model.state_dict().items()} if baseline is not None and improved_validation_score(baseline,-math.inf) else None
    for epoch in range(args.epochs):
        train=[r for r in rows if r['split']=='train']; random.shuffle(train)
        model.train()
        losses=[]
        sample_count=0
        for offset in range(0,len(train),args.batch_size):
            if expired():
                stopped_for_time=True
                break
            group=train[offset:offset+args.batch_size]
            optimizer.zero_grad(); loss=model(**batch_sample(group)).loss
            losses.append(float(loss.detach().cpu())*len(group))
            sample_count+=len(group)
            loss.backward(); optimizer.step()
        validation=evaluate('validation')
        if validation is None:
            stopped_for_time=True
        history.append({'epoch':epoch+1,'train_loss':sum(losses)/sample_count if sample_count else None,'training_samples':sample_count,'validation':validation,'validation_complete':validation is not None,'elapsed_seconds':time.monotonic()-started})
        if validation is not None and improved_validation_score(validation, best_score):
            best_score=validation['f1']
            selected_epoch=epoch+1
            best_state={key:value.detach().cpu().clone() for key,value in model.state_dict().items()}
        print(json.dumps(history[-1]),flush=True)
        if stopped_for_time:
            break
    if best_state is None and stopped_for_time and baseline_state is not None:
        best_state=baseline_state
        selected_epoch=0
        best_score=baseline['f1']
    if best_state is None:
        raise ValueError('No epoch had a finite validation F1; refusing to publish a checkpoint')
    model.load_state_dict(best_state)
    model.save_pretrained(out/'model'); processor.save_pretrained(out/'model')
    metadata={
        'model_id':str((out/'model').resolve()),
        'checkpoint_id':checkpoint_identity(out/'model'),
        'run_id':run_id, 'task':FLOOD_TASK,
        'requires_road_roi':True,
        'label_map':{'0':'non_flooded_road','1':'flooded_road'},
        'identity_status':'verified',
        'native_tile_size':256 if args.native_tile_inference else None,
        'training_resolution':{'height':256,'width':256},
        'initialization_model_id':DEFAULT_MODEL,
        'initialization_revision':DEFAULT_REVISION,
        'selected_epoch':selected_epoch,
        'selection_metric':'validation.f1', 'selection_score':best_score,
        'training_settings':{'requested_device':args.device,'device':device,'threads':args.threads,'learning_rate':args.learning_rate,'batch_size':args.batch_size,'freeze_backbone':args.freeze_backbone,'max_seconds':args.max_seconds,'skip_test':args.skip_test,'native_tile_inference':args.native_tile_inference,'save_baseline_model':args.save_baseline_model},
        'timing':{'budget_scope':'after_model_setup_between_batches','stopped_for_time':stopped_for_time,'elapsed_seconds':time.monotonic()-started},
    }
    for destination in [out/'run_metadata.json',out/'model'/'run_metadata.json']:
        destination.write_text(json.dumps(metadata,indent=2))
    final_metrics=None if args.skip_test else evaluate('test')
    if final_metrics is None:
        final_metrics={'status':'not_evaluated','reason':'skip_test' if args.skip_test else 'time_budget_exhausted'}
    else:
        final_metrics['status']='evaluated'
    final_metrics.update({'provenance':metadata,'split':'test','selected_epoch':selected_epoch})
    (out/'final_metrics.json').write_text(json.dumps(final_metrics,indent=2))
    (out/'evaluation_config.json').write_text(json.dumps({'seed':args.seed,'epochs':args.epochs,'device':device,'rows':rows,'history':history,'provenance':metadata,'selected_epoch':selected_epoch},indent=2))
if __name__=='__main__': main()
