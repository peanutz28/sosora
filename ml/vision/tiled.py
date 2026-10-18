"""Native-resolution sliding-window inference for road-corridor checkpoints."""
import numpy as np
import torch
from PIL import Image


def _positions(length, size, stride):
    if length <= size:
        return [0]
    return sorted(set(range(0, length-size+1, stride)) | {length-size})


def tiled_probabilities(model, processor, image, tile_size=256, stride=None):
    if tile_size < 16:
        raise ValueError('tile_size must be at least 16')
    stride = stride or tile_size
    if not 1 <= stride <= tile_size:
        raise ValueError('stride must be between 1 and tile_size')
    image = image.convert('RGB')
    width, height = image.size
    total = None
    count = np.zeros((height,width),dtype=np.float32)
    try:
        device = next(model.parameters()).device
    except (StopIteration, AttributeError):
        device = 'cpu'
    with torch.inference_mode():
        for y in _positions(height,tile_size,stride):
            for x in _positions(width,tile_size,stride):
                w,h=min(tile_size,width-x),min(tile_size,height-y)
                tile=Image.new('RGB',(tile_size,tile_size))
                tile.paste(image.crop((x,y,x+w,y+h)),(0,0))
                batch=processor(images=tile,return_tensors='pt')
                batch={k:v.to(device) for k,v in batch.items()}
                logits=model(**batch).logits
                probs=torch.nn.functional.interpolate(logits,size=(tile_size,tile_size),mode='bilinear',align_corners=False).softmax(1)[0].cpu().numpy()[:,:h,:w]
                if total is None:
                    total=np.zeros((probs.shape[0],height,width),dtype=np.float32)
                total[:,y:y+h,x:x+w]+=probs
                count[y:y+h,x:x+w]+=1
    return total/count[None,:,:]
