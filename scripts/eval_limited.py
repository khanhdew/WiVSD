"""Limited evaluator: process up to N CSVs per target directory and save a summary.

Usage:
    python scripts/eval_limited.py --root . --limit 10 --out reports/eval_summary_limited.json
"""
from pathlib import Path
import argparse
import json
import tempfile
import re

from csi_preprocessing.dataset import preprocess_csv_pipeline
from csi_preprocessing.classifier import predict_from_npz


def _normalize_part(part: str) -> str:
    return re.sub(r"[\W_]+", " ", part.lower()).strip()


def infer_label_from_path(p: Path):
    for part in p.parts:
        norm = _normalize_part(part)
        if 'no person' in norm or 'noperson' in norm:
            return 0
    for part in p.parts:
        norm = _normalize_part(part)
        if 'router' in norm:
            return 1
    return None


def find_csvs(root: Path, subdir: str):
    d = root / subdir
    if not d.exists():
        return []
    # Search recursively to include CSVs inside nested subdirectories
    return sorted([p for p in d.rglob('*.csv')])


def run(root: Path, limit: int, out: Path):
    root = Path(root)
    targets = ['Router', 'router no person']
    results = []

    for t in targets:
        csvs = find_csvs(root, t)[:limit]
        for c in csvs:
            gt = infer_label_from_path(c)
            with tempfile.TemporaryDirectory() as td:
                out_dir = Path(td) / (c.stem + '_out')
                try:
                    preprocess_csv_pipeline(c, out_dir)
                except Exception as e:
                    results.append({'path': str(c), 'ground_truth': gt, 'prediction': None, 'error': str(e)})
                    continue
                npz = out_dir / 'dataset.npz'
                if not npz.exists():
                    results.append({'path': str(c), 'ground_truth': gt, 'prediction': None, 'error': 'no_npz'})
                    continue
                pred, details = predict_from_npz(npz)
                results.append({'path': str(c), 'ground_truth': gt, 'prediction': int(pred), 'details': details})

    # metrics
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
    parser.add_argument('--limit', type=int, required=False, default=10)
    parser.add_argument('--out', type=Path, required=False, default=Path('reports/eval_summary_limited.json'))
    args = parser.parse_args()
    s = run(args.root, args.limit, args.out)
    print(json.dumps(s, indent=2))
