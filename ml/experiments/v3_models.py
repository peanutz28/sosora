"""One raw-checkpoint adapter shared by final scoring and optional local serving."""
from types import SimpleNamespace
from pathlib import Path
import torch
from ml.experiments.train_comparator import make_model


class VisionAdapter(torch.nn.Module):
    def __init__(self,model):
        super().__init__();self.model=model
        self.config=getattr(model,'config',SimpleNamespace(
            id2label={0:'non_flooded_road',1:'flooded_road'},num_labels=2,
            sosora_tile_size=256,requires_road_roi=True,_commit_hash=None))
        self.config.sosora_tile_size=256
        self.config.requires_road_roi=True

    def forward(self,pixel_values):
        output=self.model(pixel_values)
        return SimpleNamespace(logits=output) if isinstance(output,torch.Tensor) else output


def load_candidate(architecture,checkpoint,base):
    if not Path(checkpoint).is_file():raise ValueError('Missing selected raw checkpoint')
    model=make_model(architecture,str(base))
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True),strict=True)
    return VisionAdapter(model).eval()
