"""Bundle only reviewed train/dev crops and local initialization; no final pixels/labels/secrets."""
import argparse
import json
from pathlib import Path
import tarfile
from ml.experiments.v3_protocol import ROOT, MANIFEST_SHA256, preflight, sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    preflight()
    manifest=ROOT/'ml/artifacts/v3_experiment/reviewed_crop_manifest.json'
    rows=json.loads(manifest.read_text())
    files=set((ROOT/'ml/experiments').glob('*.py'))
    files.update(ROOT/path for path in ['ml/artifacts/v3_experiment/reviewed_crop_manifest.json',
        'ml/artifacts/v3_experiment/readiness.json','ml/artifacts/v3_experiment/protocol.json',
        'ml/artifacts/v3_experiment/final_seal.json','scripts/ml/gpu_check.py'])
    files.update((ROOT/'ml/artifacts/sn8_native_cpu_v2/baseline_model').glob('*'))
    for row in rows:
        files.update(Path(row[key]) for key in ('image','mask'))
    files={path for path in files if path.is_file()}
    receipt={'manifest_sha256':MANIFEST_SHA256,'final_pixels_or_labels_included':False,'files':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(args.output,'w:gz',compresslevel=1) as archive:
        for path in sorted(files):
            relative=path.relative_to(ROOT).as_posix()
            if any(part.startswith('.env') for part in path.parts) or relative.endswith('.csv'):
                raise ValueError('Refusing credentials or global annotation CSV')
            archive.add(path,arcname=relative,recursive=False)
            receipt['files'].append({'path':relative,'bytes':path.stat().st_size,'sha256':sha256(path)})
    receipt.update(archive_bytes=args.output.stat().st_size,archive_sha256=sha256(args.output))
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'files':len(files),'archive_bytes':receipt['archive_bytes'],'archive_sha256':receipt['archive_sha256']}))


if __name__=='__main__':main()
