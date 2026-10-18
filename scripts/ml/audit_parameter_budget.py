"""Count pinned public checkpoint metadata, offline by default; no GPU or full weights.

Optional --fetch retrieves safetensors headers and the Parakeet state-dict pickle
metadata using bounded HTTP Range requests. The pickle is decoded by a restricted
metadata-only reader that never imports torch, instantiates models or reads storages.
"""
import argparse
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import pickle
import struct
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/evidence/param_budget_2026-10-18'
REVISIONS = {
    'nemotron': ('nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16', 'a9904d24bcc1d289a1950fa9d2b978c47cf903b9'),
    'parakeet': ('nvidia/parakeet-tdt-0.6b-v2', 'ae9ad07059c7c739ffaf932226a8fe64ae2620b0'),
}


def read(name):
    return json.loads((EVIDENCE / name).read_text())


def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2) + '\n')


def url(model, filename):
    repo, revision = REVISIONS[model]
    return f'https://huggingface.co/{repo}/resolve/{revision}/{filename}'


def tensor_metadata(storage, offset, size, stride, requires_grad, hooks):
    return {'storage': storage, 'storage_offset': offset, 'shape': list(size),
            'stride': list(stride), 'requires_grad': requires_grad}


class MetadataReader(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {('collections', 'OrderedDict'): OrderedDict,
                   ('torch', 'FloatStorage'): 'F32', ('torch', 'LongStorage'): 'I64',
                   ('torch._utils', '_rebuild_tensor_v2'): tensor_metadata}
        if (module, name) not in allowed:
            raise ValueError(f'Unapproved pickle global: {module}.{name}')
        return allowed[module, name]

    def persistent_load(self, item):
        if len(item) != 5 or item[0] != 'storage' or item[1] not in {'F32', 'I64'}:
            raise ValueError('Unexpected storage metadata')
        return {'dtype': item[1], 'key': item[2], 'location': item[3], 'storage_elements': item[4]}


def parakeet_is_buffer(name):
    return (name in {'preprocessor.featurizer.window', 'preprocessor.featurizer.fb'}
            or name.endswith(('.running_mean', '.running_var', '.num_batches_tracked')))


class RemoteFile(io.RawIOBase):
    """Seekable bounded metadata reads; never reads an entire checkpoint storage."""
    def __init__(self, source, length, receipts, offset=0):
        self.source, self.length, self.receipts, self.offset = source, length, receipts, offset
        self.pos = 0

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.length + offset
        if self.pos < 0:
            raise ValueError('Negative seek')
        return self.pos

    def read(self, size=-1):
        size = self.length - self.pos if size < 0 else min(size, self.length - self.pos)
        if size <= 0: return b''
        if size > 8 * 1024**2:
            raise ValueError('Refusing oversized metadata read')
        start = self.offset + self.pos; end = start + size - 1
        request = urllib.request.Request(self.source + f'?audit_range={start}-{end}',
                                         headers={'Range': f'bytes={start}-{end}'})
        with urllib.request.urlopen(request, timeout=60) as response:
            content_range = response.headers.get('Content-Range', '')
            if response.status != 206 or not content_range.startswith(f'bytes {start}-{end}/'):
                raise ValueError('Server did not honor requested metadata byte range')
            data = response.read(size + 1)
            if len(data) != size: raise ValueError('Incorrect range length')
        self.receipts.append({'source_url': self.source, 'start': start, 'end': end, 'bytes': size,
                              'content_range': content_range, 'sha256': hashlib.sha256(data).hexdigest()})
        self.pos += size
        return data


def fetch():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipts = []
    index_source = url('nemotron', 'model.safetensors.index.json')
    with urllib.request.urlopen(index_source, timeout=60) as response:
        raw = response.read(4 * 1024**2)
    (EVIDENCE / 'nemotron.model.safetensors.index.json').write_bytes(raw)
    index = json.loads(raw)
    (EVIDENCE / 'nemotron_headers').mkdir(exist_ok=True)
    for name in sorted(set(index['weight_map'].values())):
        remote = RemoteFile(url('nemotron', name), 8 * 1024**2, receipts)
        length = struct.unpack('<Q', remote.read(8))[0]
        header = remote.read(length)
        json.loads(header)
        (EVIDENCE / 'nemotron_headers' / (name + '.json')).write_bytes(header)
    # The saved public range probe records the immutable archive length.
    length = int(read('parakeet_range_probe.json')['Content-Range'].split('/')[-1])
    source = url('parakeet', 'parakeet-tdt-0.6b-v2.nemo')
    with tarfile.open(fileobj=RemoteFile(source, length, receipts), mode='r:') as archive:
        member = None
        for item in archive:
            if item.name.endswith('/model_config.yaml'):
                (EVIDENCE / 'parakeet.model_config.yaml').write_bytes(archive.extractfile(item).read())
            if item.name.endswith('/model_weights.ckpt'):
                member = item; break
        if member is None: raise ValueError('Missing model_weights.ckpt')
    save('parakeet_tar_member.json', {'name': member.name, 'offset_data': member.offset_data, 'size': member.size})
    with zipfile.ZipFile(RemoteFile(source, member.size, receipts, member.offset_data)) as checkpoint:
        names = [n for n in checkpoint.namelist() if n.endswith('/data.pkl')]
        if len(names) != 1: raise ValueError('Ambiguous state-dict metadata')
        (EVIDENCE / 'parakeet.model_weights.data.pkl').write_bytes(checkpoint.read(names[0]))
    save('fetch_receipts.json', {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                                'bytes_read': sum(r['bytes'] for r in receipts), 'requests': receipts})


def count():
    index = read('nemotron.model.safetensors.index.json')
    receipts = {r['file']: r for r in read('nemotron_header_receipts.json')}
    tensors = {}; groups = defaultdict(Counter)
    for path in sorted((EVIDENCE / 'nemotron_headers').glob('*.json')):
        raw = path.read_bytes(); receipt = receipts[path.name[:-5]]
        if hashlib.sha256(raw).hexdigest() != receipt['header_sha256']:
            raise ValueError('Header differs from pinned fetch receipt')
        header = json.loads(raw)
        spans = sorted(t['data_offsets'] for n,t in header.items() if n != '__metadata__')
        if spans[0][0] != 0 or any(a[1] != b[0] for a,b in zip(spans,spans[1:])):
            raise ValueError('Noncontiguous or overlapping tensor payloads')
        if spans[-1][1] + 8 + len(raw) != int(receipt['Content-Range'].split('/')[-1]):
            raise ValueError('Tensor payload extent differs from shard byte length')
        for name, tensor in header.items():
            if name == '__metadata__': continue
            if name in tensors or index['weight_map'].get(name) != path.name[:-5]:
                raise ValueError('Duplicate tensor or wrong shard')
            tensor = {**tensor, 'shard': path.name[:-5], 'numel': math.prod(tensor['shape'])}
            is_buffer = name.endswith('.e_score_correction_bias')
            if tensor['dtype'] != ('F32' if is_buffer else 'BF16'):
                raise ValueError('Unexpected checkpoint dtype/classification')
            if tensor['data_offsets'][1]-tensor['data_offsets'][0] != tensor['numel']*(4 if is_buffer else 2):
                raise ValueError('Shape and byte extent disagree')
            tensor['is_buffer'] = is_buffer; tensors[name] = tensor
            groups[tensor['dtype']].update(tensors=1, elements=tensor['numel'],
                                            bytes=tensor['data_offsets'][1]-tensor['data_offsets'][0])
    if set(tensors) != set(index['weight_map']): raise ValueError('Incomplete shard inventory')
    nemotron_params = sum(t['numel'] for t in tensors.values() if not t['is_buffer'])
    core = sum(t['numel'] for n,t in tensors.items() if not t['is_buffer'] and not n.startswith('mtp.'))
    if core != index['metadata']['total_parameters']: raise ValueError('Core count does not reconcile')
    save('nemotron_counts.json', {'full_checkpoint_parameters_including_mtp': nemotron_params,
        'core_parameters_excluding_mtp': core, 'mtp_parameters': nemotron_params-core,
        'all_tensor_elements': sum(t['numel'] for t in tensors.values()),
        'routing_buffer_elements': sum(t['numel'] for t in tensors.values() if t['is_buffer']),
        'tensor_count': len(tensors), 'by_dtype': groups, 'index_metadata': index['metadata'],
        'index_total_size_divided_by_2': index['metadata']['total_size']//2,
        'index_tensor_names_and_shards_match': True, 'method': 'Sum product(shape) from every pinned shard header; exclude only declared routing buffers; include MTP.'})
    raw = (EVIDENCE / 'parakeet.model_weights.data.pkl').read_bytes()
    if hashlib.sha256(raw).hexdigest() != read('parakeet_checkpoint_structure.json')['pickle_sha256']:
        raise ValueError('Checkpoint metadata differs from pinned fetch receipt')
    state = MetadataReader(io.BytesIO(raw)).load()
    inventory = []
    for name, tensor in state.items():
        if not isinstance(tensor,dict) or 'shape' not in tensor: raise ValueError('Unexpected state entry')
        inventory.append({'name': name, **tensor, 'numel': math.prod(tensor['shape']),
                          'is_buffer': parakeet_is_buffer(name)})
    storages = {t['storage']['key']: t['storage']['storage_elements'] for t in inventory}
    if sum(storages.values()) != sum(t['numel'] for t in inventory):
        raise ValueError('Shared storage or views require an explicit alias audit')
    save('parakeet_tensor_inventory.json', inventory)
    asr_params = sum(t['numel'] for t in inventory if not t['is_buffer'])
    save('parakeet_counts.json', {'parameters': asr_params, 'all_tensor_elements': sum(t['numel'] for t in inventory),
        'buffer_elements': sum(t['numel'] for t in inventory if t['is_buffer']),
        'parameter_tensors': sum(not t['is_buffer'] for t in inventory), 'buffer_tensors': sum(t['is_buffer'] for t in inventory),
        'pickle_sha256': hashlib.sha256(raw).hexdigest(), 'requires_grad_not_used': True,
        'method': 'Restricted metadata-only pickle parser; sum tensor shapes excluding preprocessor and BatchNorm buffers.'})
    vision = json.loads((ROOT / 'docs/ml/evidence/v3_2026-10-18/v2_dev.json').read_text())['parameters']
    cap = 33_000_000_000
    without = nemotron_params + vision; with_asr = without + asr_params
    save('totals.json', {'cap': cap, 'billion_definition': 1_000_000_000, 'nemotron_full_checkpoint_parameters': nemotron_params,
        'segformer_parameters': vision, 'parakeet_parameters': asr_params,
        'without_asr': {'parameters': without, 'under_33b': without < cap, 'headroom': cap-without},
        'with_asr': {'parameters': with_asr, 'under_33b': with_asr < cap, 'headroom': cap-with_asr},
        'scope': 'Full checkpoint includes MTP and all experts; one Nemotron and one served SegFormer. Parakeet hypothetical addition; no ASR deployment or GPU launch.'})
    print(json.dumps(read('totals.json'), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Re-fetch pinned metadata byte ranges only')
    args = parser.parse_args()
    if args.fetch: fetch()
    count()
