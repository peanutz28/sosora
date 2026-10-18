"""Build the V3 report only from saved run, selection, evaluation and shutdown evidence."""
from datetime import datetime,timezone
import json
from pathlib import Path
from ml.experiments.v3_protocol import ROOT,FREEZE_DEADLINE


def metric(value):return 'undefined' if value is None else f'{value:.6f}'


def main():
    if datetime.now(timezone.utc)>=FREEZE_DEADLINE:raise ValueError('Feature freeze reached')
    folder=ROOT/'docs/ml/evidence/v3_2026-10-18'
    read=lambda name:json.loads((folder/name).read_text())
    selection=read('selection.json');final=read('final_evaluation.json');reference=read('v2_dev.json')
    proof_choice=read('proof_selection.json')
    if read('final_evaluation_ledger.json')['status']!='complete':raise ValueError('No completed final result')
    if not read('gpu_stop.json')['verified_stopped']:raise ValueError('GPU stop must be verified before reporting completion')
    quote=read('gpu_quote.json');launch=read('launch.json');stop=read('gpu_stop.json')
    duration=(datetime.fromisoformat(stop['verified_stopped_at_utc'])-datetime.fromisoformat(launch['started_at_utc'])).total_seconds()
    cost={'elapsed_start_request_to_verified_stop_seconds':duration,'quoted_compute_usd_per_hour':quote['compute_usd_per_hour'],
        'estimated_compute_usd':duration/3600*quote['compute_usd_per_hour'],'authorized_total_usd':quote['authorized_total_usd'],
        'storage_usd_per_gb_month':quote['disk_usd_per_gb_month'],
        'caveat':'Elapsed-time estimate, not a provider invoice; retained storage is charged separately. Existing L4 disk retained.'}
    (folder/'cost_estimate.json').write_text(json.dumps(cost,indent=2)+'\n')
    attempts=read('runs/attempts.json')
    report_numbers={'v2_dev':reference['metrics'],'v3_dev':selection['dev_metrics'],
        'final':final['metrics'],'parameters':final['parameters'],'final_tile_count':final['tile_count'],
        'dev_tile_count':reference['source_tile_count'],'dev_crop_count':reference['crop_count'],
        'cost':cost,'all_attempts':attempts}
    (folder/'report_numbers.json').write_text(json.dumps(report_numbers,indent=2)+'\n')
    v2=final['metrics']['v2'];v3=final['metrics']['v3']
    sentence=f"On {final['tile_count']} sealed held-out tiles, F1 went from {metric(v2['f1'])} to {metric(v3['f1'])}."
    lines=['# V3 aerial flooded-road results','',sentence,'',
        'This is a single frozen geographic assessment within the known Louisiana and Germany events. It is not unseen-event generalization, an official SpaceNet test benchmark, or Helene accuracy.','',
        '| Model | Parameters | Initialization | Dev F1 | Final F1 | Final precision | Final recall | Final IoU |',
        '|---|---:|---|---:|---:|---:|---:|---:|']
    for role,label,initialization,dev in [('v2','Current native v2','Historical fine-tuned ADE-derived SegFormer',reference['metrics']['f1']),
            ('v3','Selected V3 '+selection['architecture'],selection['initialization'],selection['dev_metrics']['f1'])]:
        score=final['metrics'][role]
        lines.append(f"| {label} | {final['parameters'][role]:,} | {initialization} | {metric(dev)} | {metric(score['f1'])} | {metric(score['precision'])} | {metric(score['recall'])} | {metric(score['iou'])} |")
    lines+=['','All final scores use identical original road-mask pixels, the same metric code, native sliding windows and the committed decision rule. Undefined denominators remain null. Full confusion counts and every tile are in [final_evaluation.json](evidence/v3_2026-10-18/final_evaluation.json).',
        '',f"The all-flooded control has final F1 {metric(final['metrics']['all_positive']['f1'])}; the all-non-flooded control has final F1 {metric(final['metrics']['all_negative']['f1'])}. These controls expose class imbalance; they are not pretrained flood models.",
        '','## Selection and complete run accounting','',
        f"Selection was committed in `{final['selection']['selection_commit']}` before final preparation. It chose {selection['architecture']}, learning rate {selection['learning_rate']:g}, epoch {selection['selected_epoch']}, using only the {reference['crop_count']} reviewed development crops from {reference['source_tile_count']} tiles. These overlapping crops are correlated. The binary decision rule and all preparation/inference/metric source hashes were frozen in [selection.json](evidence/v3_2026-10-18/selection.json).",'',
        '| Attempt | Kind | Outcome | Selected epoch | Best dev F1 | Elapsed seconds |',
        '|---|---|---|---:|---:|---:|']
    for attempt in attempts:
        run_path=folder/'runs'/attempt['name']/'run.json'
        run=json.loads(run_path.read_text()) if run_path.exists() else {}
        lines.append(f"| {attempt['name']} | {'throughput check' if attempt['benchmark'] else 'trained candidate'} | {'completed' if attempt['returncode']==0 else 'failed; see log'} | {attempt.get('selected_epoch') or '—'} | {metric(attempt.get('best_dev_f1'))} | {metric(run.get('elapsed_seconds'))} |")
    lines+=['','Every attempted command, return code, log, checkpoint hash and epoch history is retained under [runs/](evidence/v3_2026-10-18/runs/). The short benchmark rows are throughput checks, not accuracy measurements. Learning rates and initialization differ across architectures; the bounded sweep does not establish equal optimization.',
        '','## Evidence and limits','',
        f"- Selected raw checkpoint SHA256: `{selection['checkpoint_sha256']}`.",
        f"- Unchanged native-v2 identity: `{selection['v2_checkpoint_id']}`.",
        '- [Final preparation ledger](evidence/v3_2026-10-18/final_preparation_ledger.json) and [evaluation ledger](evidence/v3_2026-10-18/final_evaluation_ledger.json) record the one-shot stages. Completed stages refuse another evaluation; only a logged failed identical request may retry.',
        '- No final tile was replaced or excluded based on outcomes. Cloud/alignment quality flags and empty-supervision tiles remain accounted for. Narrow buffered-road labels omit off-road false alarms and do not establish closures, travel safety or complete road extraction.',
        '- V3 uses more training geography than the historical v2 run; data, training and possibly architecture differ. An improvement cannot be attributed to architecture alone. The earlier frozen six-tile Germany result remains unchanged.',
        '- The stored global annotation CSVs predate this task. Final rows were not interpreted by this pipeline until the committed selection guard passed; the historical seal file was preserved unchanged.',
        '- [1920×1080 proof image](../screenshots/vision-v3-proof.png) uses saved predictions only. '+('Its first tile shows V3 regression by '+proof_choice['regression_criterion']+'.' if proof_choice['regression_found'] else 'No tile has a measured F1/FP/FN regression; a worse example cannot be fabricated.')+' No model was rerun to make the image.',
        '', '## Compute and promotion','',
        f"Only the approved L4 was used at the quoted ${quote['compute_usd_per_hour']:.6f}/hour. Its stop was verified at `{stop['verified_stopped_at_utc']}`. Elapsed-time compute estimate: ${cost['estimated_compute_usd']:.4f}; this is not an invoice and excludes retained storage. Quote, CUDA verification, shutdown evidence and cost inputs are saved in this evidence directory. Codex B's H100 was not used.",'' ]
    promotion_path=folder/'promotion.json'
    promotion=json.loads(promotion_path.read_text()) if promotion_path.exists() else None
    if promotion and promotion.get('promoted'):
        lines.append('V3 is available only behind `ML_MODEL_VERSION=v3`; the default remains unchanged. The promotion record binds the exported artifact to the selected raw checkpoint and includes the contract smoke evidence. No final re-evaluation or threshold tuning was performed.')
    else:
        lines.append('No V3 promotion is recorded; the default remains native v2. Final outcomes do not authorize further tuning on these tiles.')
    (ROOT/'docs/ml/V3_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(sentence)


if __name__=='__main__':main()
