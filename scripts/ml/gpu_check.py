import json
import shutil
import subprocess
import torch
if not torch.cuda.is_available():
    raise SystemExit('CUDA unavailable; GPU verification FAILED')
x=torch.randn(1024,1024,device='cuda'); y=x@x
assert torch.isfinite(y).all()
print(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(),'vram_bytes':torch.cuda.get_device_properties(0).total_memory,'operation':'1024x1024 matmul passed','docker':shutil.which('docker')}))
subprocess.run(['nvidia-smi'],check=True)
