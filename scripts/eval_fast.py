"""Fast evaluator using CSV-only lightweight predictor.

Usage:
    python scripts/eval_fast.py --root . --limit 20 --out reports/eval_fast_summary.json
"""
from pathlib import Path
import argparse
import json

from csi_preprocessing.classifier import predict_from_csv_fast


def infer_label_from_path(p: Path):
    for part in p.parts:
        lp = part.lower()
        if 'no person' in lp or 'noperson' in lp:
            return 0
        if 'router' in lp:
            return 1
    return None


def find_csvs(root: Path, subdir: str):
    d = root / subdir
    if not d.exists():
        return []
    return sorted([p for p in d.glob('*.csv')])


def run(root: Path, limit: int, out: Path):
    root = Path(root)
    targets = ['Router', 'router no person']
    results = []

    for t in targets:
        csvs = find_csvs(root, t)[:limit]
        for c in csvs:
            gt = infer_label_from_path(c)
            pred, details = predict_from_csv_fast(c, n_packets_max=200)
            results.append({'path': str(c), 'ground_truth': gt, 'prediction': int(pred) if pred is not None else None, 'details': details})

    tp = fp = tn = fn = 0
    total = 0
    per_sample = []
    for r in results:
        if r.get('prediction') is None or r.get('ground_truth') is None:
            continue
        gt = int(r['ground_truth'])
        pr = int(r['prediction'])
        total += 1
        if gt == 1 and pr == 1:
            tp += 1
        elif gt == 0 and pr == 1:
            fp += 1
        elif gt == 0 and pr == 0:
            tn += 1
        elif gt == 1 and pr == 0:
            fn += 1
        per_sample.append({'path': r['path'], 'gt': gt, 'pred': pr, 'details': r.get('details', {})})

    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    summary = {
        'total_samples': total,
        'tp': tp,
        'fp': fp,
        'tn': tn,
        'fn': fn,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'per_sample': per_sample,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=False, default=Path('.'))
    parser.add_argument('--limit', type=int, required=False, default=20)
    parser.add_argument('--out', type=Path, required=False, default=Path('reports/eval_fast_summary.json'))
    args = parser.parse_args()
    s = run(args.root, args.limit, args.out)
    print(json.dumps(s, indent=2))
