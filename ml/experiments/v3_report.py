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
    proof_choice=read('proof_selection.json');analysis=read('outcome_analysis.json')
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
        'cost':cost,'all_attempts':attempts,'outcome_analysis':analysis}
    (folder/'report_numbers.json').write_text(json.dumps(report_numbers,indent=2)+'\n')
    v2=final['metrics']['v2'];v3=final['metrics']['v3']
    sentence=f"On {final['tile_count']} sealed held-out tiles, F1 went from {metric(v2['f1'])} to {metric(v3['f1'])}."
    lines=['# V3 aerial flooded-road results','',sentence,'',
        ('V3 did not beat native v2 on final F1. It is not promoted; the ML service default is unchanged.' if not final['promote_v3'] else 'V3 beat native v2 on final F1; serving status is recorded below.'),'',
        'This is a single frozen geographic assessment within the known Louisiana and Germany events. It is not unseen-event generalization, an official SpaceNet test benchmark, or Helene accuracy.','',
        '| Model | Parameters | Initialization | Dev F1 | Final F1 | Final precision | Final recall | Final IoU |',
        '|---|---:|---|---:|---:|---:|---:|---:|']
    for role,label,initialization,dev in [('v2','Current native v2','Historical fine-tuned ADE-derived SegFormer',reference['metrics']['f1']),
            ('v3','Selected V3 '+selection['architecture'],selection['initialization'],selection['dev_metrics']['f1'])]:
        score=final['metrics'][role]
        lines.append(f"| {label} | {final['parameters'][role]:,} | {initialization} | {metric(dev)} | {metric(score['f1'])} | {metric(score['precision'])} | {metric(score['recall'])} | {metric(score['iou'])} |")
    lines+=['','All final scores use identical original road-mask pixels, the same metric code, native sliding windows and the committed decision rule. Undefined denominators remain null. Full confusion counts and every tile are in [final_evaluation.json](evidence/v3_2026-10-18/final_evaluation.json).',
        '',f"The all-flooded control has final F1 {metric(final['metrics']['all_positive']['f1'])}; the all-non-flooded control has final F1 {metric(final['metrics']['all_negative']['f1'])}. These controls expose class imbalance; they are not pretrained flood models.",
        '',f"Across {v2['valid_pixels']:,} identical scored pixels, V3 has {v3['fp']:,} false positives versus v2's {v2['fp']:,}, and {v3['fn']:,} missed flooded pixels versus {v2['fn']:,}. Its higher recall did not offset its lower precision. Tiles with no scored road pixels: {analysis['empty_supervision_tile_count']} of {final['tile_count']}; these remain in the manifest and per-tile results with undefined metrics. Overall scores pool labeled pixels rather than averaging tile F1.",
        '', 'Descriptive regional counts below are aggregates of the saved final confusion counts; they do not select another winner or trigger another evaluation.', '',
        '| Known event region | Tiles | Scored pixels | Flooded pixels | v2 F1 | V3 F1 |',
        '|---|---:|---:|---:|---:|---:|']
    for region,record in analysis['by_region'].items():
        lines.append(f"| {region} | {record['tile_count']} | {record['v2']['valid_pixels']:,} | {record['v2']['tp']+record['v2']['fn']:,} | {metric(record['v2']['f1'])} | {metric(record['v3']['f1'])} |")
        if record['v2']['tp']+record['v2']['fn']==0:
            lines.append(f"\nThe sealed {region} block has no positive flooded-road labels, so flooded-road recall there is undefined. It checks false alarms on its labeled road corridors: {record['v2']['fp']:,} for v2 and {record['v3']['fp']:,} for V3. This does not establish flooded-road recall for that region.\n")
    lines += [
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
        '- V3 uses more training geography than the historical v2 run. Both final models are SegFormer-B0; data and training differ. The development gain did not transfer to this sealed set. Clouds, label alignment and sampling are limitations, not proven causes of the regression. The earlier frozen six-tile Germany result remains unchanged.',
        '- Data: [SpaceNet 8 / SpaceNet Partners and Maxar](https://spacenet.ai/sn8-challenge/), licensed CC BY-SA 4.0. Source URLs and processing changes are listed in [data_attribution.json](evidence/v3_2026-10-18/data_attribution.json); the derived proof image retains that attribution/license.',
        '- The stored global annotation CSVs predate this task. Final rows were not interpreted by this pipeline until the committed selection guard passed; the historical seal file was preserved unchanged.',
        '- [1920×1080 proof image](../screenshots/vision-v3-proof.png) uses saved predictions only. '+('Its first tile shows V3 regression by '+proof_choice['regression_criterion']+'.' if proof_choice['regression_found'] else 'No tile has a measured F1/FP/FN regression; a worse example cannot be fabricated.')+' No model was rerun to make the image.',
        '', '## Compute and promotion','',
        f"Only the approved L4 was used at the quoted ${quote['compute_usd_per_hour']:.6f}/hour. Its stop was verified at `{stop['verified_stopped_at_utc']}`. Elapsed-time compute estimate: ${cost['estimated_compute_usd']:.4f}; this is not an invoice and excludes retained storage. Quote, CUDA verification, shutdown evidence and cost inputs are saved in this evidence directory. Codex B's H100 was not used.",'' ]
    promotion_path=folder/'promotion.json'
    promotion=json.loads(promotion_path.read_text()) if promotion_path.exists() else None
    if promotion and promotion.get('promoted'):
        lines.append('V3 is available only behind `ML_MODEL_VERSION=v3`; the default remains unchanged. The promotion record binds the exported artifact to the selected raw checkpoint and includes the contract smoke evidence. No final re-evaluation or threshold tuning was performed.')
    else:
        lines.append('No V3 promotion: the selected checkpoint lost on final F1, so no environment gate or serving changes were added. The default remains native v2. No ML service restart was needed. The final set is now spent for model selection; future tuning requires a fresh held-out evaluation set.')
    (ROOT/'docs/ml/V3_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(sentence)


if __name__=='__main__':main()
