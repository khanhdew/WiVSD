"""Tune simple amp_cv / amp_std thresholds using the per-sample eval JSON.

Usage:
    python scripts/tune_threshold.py --in reports/eval_fast_summary.json --out reports/threshold_tuning.json
"""
import json
from pathlib import Path
import numpy as np
import argparse


def load_eval(path: Path):
    j = json.loads(path.read_text(encoding='utf-8'))
    return j


def score_preds(gts, preds):
    tp = sum(1 for g,p in zip(gts,preds) if g==1 and p==1)
    tn = sum(1 for g,p in zip(gts,preds) if g==0 and p==0)
    fp = sum(1 for g,p in zip(gts,preds) if g==0 and p==1)
    fn = sum(1 for g,p in zip(gts,preds) if g==1 and p==0)
    total = len(gts)
    accuracy = (tp+tn)/total if total else 0.0
    precision = tp/(tp+fp) if (tp+fp) else 0.0
    recall = tp/(tp+fn) if (tp+fn) else 0.0
    f1 = 2*precision*recall/(precision+recall) if (precision+recall) else 0.0
    return {'tp':tp,'tn':tn,'fp':fp,'fn':fn,'accuracy':accuracy,'precision':precision,'recall':recall,'f1':f1}


def run(in_path: Path, out_path: Path):
    data = load_eval(in_path)
    samples = data.get('per_sample', [])
    rows = []
    for s in samples:
        d = s.get('details', {})
        rows.append({'path': s.get('path'), 'gt': s.get('gt'), 'amp_cv': d.get('amp_cv'), 'amp_std': d.get('amp_std')})
    # filter only rows with numeric features
    rows = [r for r in rows if r['amp_cv'] is not None and r['amp_std'] is not None]
    if not rows:
        raise SystemExit('No rows with amp_cv/amp_std found in input')

    gts = np.array([r['gt'] for r in rows])
    cvs = np.array([float(r['amp_cv']) for r in rows])
    stds = np.array([float(r['amp_std']) for r in rows])

    best = {'f1': -1}
    # coarse grid
    cv_threshs = np.linspace(0.0, 0.5, 51)
    std_threshs = np.linspace(0.0, 60.0, 121)
    for cvt in cv_threshs:
        for st in std_threshs:
            preds = ((cvs > cvt) | (stds > st)).astype(int)
            metrics = score_preds(gts, preds)
            if metrics['f1'] > best['f1']:
                best = {'f1': metrics['f1'], 'cv_thresh': float(cvt), 'std_thresh': float(st), 'metrics': metrics}
    # also find threshold optimizing accuracy
    best_acc = {'accuracy': -1}
    for cvt in cv_threshs:
        for st in std_threshs:
            preds = ((cvs > cvt) | (stds > st)).astype(int)
            metrics = score_preds(gts, preds)
            if metrics['accuracy'] > best_acc['accuracy']:
                best_acc = {'accuracy': metrics['accuracy'], 'cv_thresh': float(cvt), 'std_thresh': float(st), 'metrics': metrics}

    out = {'best_f1': best, 'best_accuracy': best_acc, 'total_samples': len(rows)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', dest='infile', type=Path, default=Path('reports/eval_fast_summary.json'))
    parser.add_argument('--out', dest='outfile', type=Path, default=Path('reports/threshold_tuning.json'))
    args = parser.parse_args()
    run(args.infile, args.outfile)
