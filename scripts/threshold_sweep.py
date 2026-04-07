#!/usr/bin/env python3
"""Threshold sweep script: compute precision/recall/F1 for thresholds on holdout.

Saves JSON report and a PNG plot.

Usage example:
  python scripts/threshold_sweep.py --root . --model models/rf_person_detector_retrained.joblib --pos-dir holdout/Router --neg-dir "holdout/router no person" --out reports/threshold_sweep_holdout.json --plot reports/threshold_sweep_holdout.png
"""
from pathlib import Path
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from joblib import load
from sklearn.metrics import precision_recall_curve, roc_curve, auc, precision_score, recall_score, f1_score

from csi_preprocessing.classifier import predict_from_csv_fast


def gather_csvs(src: Path):
    if not src.exists():
        return []
    return sorted([p for p in src.glob('*.csv')])


def collect_holdout_features(pos_dir: Path, neg_dir: Path, n_packets_max: int = 200):
    X = []
    y = []
    paths = []
    details_list = []

    for p in gather_csvs(pos_dir):
        try:
            _, details = predict_from_csv_fast(p, n_packets_max=n_packets_max)
        except Exception:
            continue
        if not isinstance(details, dict):
            continue
        feat = [details.get('amp_mean'), details.get('amp_std'), details.get('amp_cv')]
        if None in feat:
            continue
        X.append(feat)
        y.append(1)
        paths.append(str(p))
        details_list.append(details)

    for p in gather_csvs(neg_dir):
        try:
            _, details = predict_from_csv_fast(p, n_packets_max=n_packets_max)
        except Exception:
            continue
        if not isinstance(details, dict):
            continue
        feat = [details.get('amp_mean'), details.get('amp_std'), details.get('amp_cv')]
        if None in feat:
            continue
        X.append(feat)
        y.append(0)
        paths.append(str(p))
        details_list.append(details)

    return np.array(X), np.array(y), paths, details_list


def run(args):
    model = load(args.model)
    pos = Path(args.pos_dir)
    neg = Path(args.neg_dir)
    X, y, paths, details = collect_holdout_features(pos, neg, n_packets_max=args.n_packets)
    if X.shape[0] == 0:
        raise SystemExit('No holdout samples found or failed to extract features')

    probs = model.predict_proba(X)[:, 1]

    # Precision-Recall curve and threshold sweep
    precision, recall, pr_thresholds = precision_recall_curve(y, probs)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-12)

    # thresholds from precision_recall_curve has len = len(precision)-1
    ths = np.concatenate(([0.0], pr_thresholds, [1.0]))
    precs = np.concatenate((precision, [precision[-1]]))
    recs = np.concatenate((recall, [recall[-1]]))
    f1s = np.concatenate((f1_scores, [f1_scores[-1]]))

    best_idx = int(np.nanargmax(f1s))
    best_threshold = float(ths[best_idx])
    best_f1 = float(f1s[best_idx])
    best_precision = float(precs[best_idx])
    best_recall = float(recs[best_idx])

    # ROC
    fpr, tpr, roc_th = roc_curve(y, probs)
    roc_auc = float(auc(fpr, tpr))

    out = {
        'n_samples': int(X.shape[0]),
        'n_pos': int(np.sum(y == 1)),
        'n_neg': int(np.sum(y == 0)),
        'best_threshold': best_threshold,
        'best_f1': best_f1,
        'best_precision': best_precision,
        'best_recall': best_recall,
        'roc_auc': roc_auc,
        'thresholds': [float(x) for x in ths.tolist()],
        'precision': [float(x) for x in precs.tolist()],
        'recall': [float(x) for x in recs.tolist()],
        'f1': [float(x) for x in f1s.tolist()],
        'per_sample': [{'path': p, 'label': int(lbl), 'proba': float(prob)} for p, lbl, prob in zip(paths, y.tolist(), probs.tolist())]
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding='utf-8')

    # Plot
    fig, ax = plt.subplots(2, 1, figsize=(8, 10))
    ax[0].plot(ths, precs, label='Precision')
    ax[0].plot(ths, recs, label='Recall')
    ax[0].plot(ths, f1s, label='F1')
    ax[0].axvline(best_threshold, color='k', linestyle='--', label=f'best t={best_threshold:.3f}')
    ax[0].set_xlabel('Threshold')
    ax[0].set_ylabel('Score')
    ax[0].legend()
    ax[0].grid(True)

    ax2 = ax[1]
    ax2.plot(fpr, tpr, label=f'ROC AUC={roc_auc:.3f}')
    ax2.plot([0, 1], [0, 1], linestyle='--', color='gray')
    ax2.set_xlabel('FPR')
    ax2.set_ylabel('TPR')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plot_path = Path(args.plot)
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(plot_path)
    print(f'Saved report to {out_path} and plot to {plot_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--pos-dir', type=str, required=True)
    parser.add_argument('--neg-dir', type=str, required=True)
    parser.add_argument('--out', type=Path, default=Path('reports/threshold_sweep.json'))
    parser.add_argument('--plot', type=Path, default=Path('reports/threshold_sweep.png'))
    parser.add_argument('--n-packets', type=int, default=200)
    args = parser.parse_args()
    run(args)
