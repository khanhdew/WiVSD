"""Train a simple ML classifier from CSV-derived features and save model+report.

Usage:
    python scripts/train_ml_classifier.py --root . --limit 200 --model models/rf_person_detector.joblib --out reports/model_train_eval.json
"""
from pathlib import Path
import argparse
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from joblib import dump, Parallel, delayed

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


def _extract_features_for_csv(c: Path, label: int, n_packets_max: int = 200):
    try:
        pred, details = predict_from_csv_fast(c, n_packets_max=n_packets_max)
    except Exception:
        return None
    if isinstance(details, dict) and details.get('error'):
        return None
    amp_mean = details.get('amp_mean')
    amp_std = details.get('amp_std')
    amp_cv = details.get('amp_cv')
    if amp_mean is None or amp_std is None or amp_cv is None:
        return None
    return [float(amp_mean), float(amp_std), float(amp_cv)], int(label), {'path': str(c), 'label': int(label), 'details': details}


def collect_features(root: Path, limit: int = None, n_jobs: int = -1, n_packets_max: int = 200):
    root = Path(root)
    targets = [('Router', 1), ('router no person', 0)]
    X = []
    y = []
    details_list = []

    for subdir, label in targets:
        csvs = find_csvs(root, subdir)
        if limit:
            csvs = csvs[:limit]

        # Parallel extraction across CSVs in this subdir
        results = Parallel(n_jobs=n_jobs)(
            delayed(_extract_features_for_csv)(c, label, n_packets_max) for c in csvs
        )

        for res in results:
            if not res:
                continue
            feat, lbl, det = res
            X.append(feat)
            y.append(lbl)
            details_list.append(det)

    return np.array(X), np.array(y), details_list


def run(root: Path, limit: int, model_out: Path, report_out: Path):
    X, y, details = collect_features(root, limit=limit)
    if X.shape[0] < 10:
        raise SystemExit('Not enough samples to train (found {})'.format(X.shape[0]))

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipe = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1))
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary', zero_division=0)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    model_out.parent.mkdir(parents=True, exist_ok=True)
    dump(pipe, model_out)

    out = {
        'n_samples': int(X.shape[0]),
        'n_features': int(X.shape[1]),
        'accuracy': acc,
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'model_path': str(model_out),
        'report': report,
        'sample_details': details[:50]
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--model', type=Path, default=Path('models/rf_person_detector.joblib'))
    parser.add_argument('--out', type=Path, default=Path('reports/model_train_eval.json'))
    args = parser.parse_args()
    run(args.root, args.limit, args.model, args.out)
