"""Train a simple ML classifier from CSV-derived features and save model+report.

Usage:
    python scripts/train_ml_classifier.py --root . --limit 200 --model models/rf_person_detector.joblib --out reports/model_train_eval.json

New options:
    --pos-train DIR [DIR ...]   directories (relative to --root or absolute) containing positive samples for training
    --neg-train DIR [DIR ...]   directories containing negative samples for training
    --pos-test DIR [DIR ...]    optional directories containing positive samples for testing (if provided, skip random split)
    --neg-test DIR [DIR ...]    optional directories containing negative samples for testing
"""
from pathlib import Path
import argparse
import json
from typing import Optional
import re
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from joblib import dump, Parallel, delayed

from csi_preprocessing.classifier import predict_from_csv_fast


def infer_label_from_path(p: Path):
    def _normalize_part(part: str) -> str:
        return re.sub(r"[\W_]+", " ", part.lower()).strip()

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


def _resolve_dir_candidate(root: Path, candidate: Path) -> Optional[Path]:
    p = Path(candidate)
    if p.is_absolute():
        return p if p.exists() else None
    cand = root / p
    return cand if cand.exists() else None


def gather_csvs_for_dirs(root: Path, dirs: Optional[list], limit: Optional[int] = None):
    if not dirs:
        return []
    out = []
    for d in dirs:
        cand = _resolve_dir_candidate(root, d)
        if not cand:
            continue
        # allow nested experiment subfolders
        files = sorted([p for p in cand.rglob('*.csv')])
        if limit:
            files = files[:limit]
        out.extend(files)
    return out


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


def collect_features(root: Path, pos_dirs: Optional[list] = None, neg_dirs: Optional[list] = None, limit: int = None, n_jobs: int = -1, n_packets_max: int = 200):
    """Collect features from directories.

    - If `pos_dirs`/`neg_dirs` are None, defaults to ['Router'] and ['router no person'] under `root`.
    - `pos_dirs` and `neg_dirs` are lists of Path or strings; non-absolute paths are resolved under `root`.
    - Returns (X, y, details_list)
    """
    root = Path(root)
    X = []
    y = []
    details_list = []

    if pos_dirs is None and neg_dirs is None:
        targets = [('Router', 1), ('router no person', 0)]
        for subdir, label in targets:
            csvs = find_csvs(root, subdir)
            if limit:
                csvs = csvs[:limit]
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
    else:
        # Gather positives
        pos_csvs = gather_csvs_for_dirs(root, pos_dirs, limit)
        neg_csvs = gather_csvs_for_dirs(root, neg_dirs, limit)

        results_pos = Parallel(n_jobs=n_jobs)(
            delayed(_extract_features_for_csv)(c, 1, n_packets_max) for c in pos_csvs
        )
        results_neg = Parallel(n_jobs=n_jobs)(
            delayed(_extract_features_for_csv)(c, 0, n_packets_max) for c in neg_csvs
        )

        for res in results_pos + results_neg:
            if not res:
                continue
            feat, lbl, det = res
            X.append(feat)
            y.append(lbl)
            details_list.append(det)

    return np.array(X), np.array(y), details_list


def run(root: Path, limit: int, model_out: Path, report_out: Path, pos_train_dirs: Optional[list] = None, neg_train_dirs: Optional[list] = None, pos_test_dirs: Optional[list] = None, neg_test_dirs: Optional[list] = None):
    # Collect training features
    X, y, details = collect_features(root, pos_dirs=pos_train_dirs, neg_dirs=neg_train_dirs, limit=limit)
    if X.shape[0] < 10:
        raise SystemExit('Not enough samples to train (found {})'.format(X.shape[0]))

    # If explicit test dirs provided, collect test set from them, else split
    if pos_test_dirs or neg_test_dirs:
        X_test, y_test, test_details = collect_features(root, pos_dirs=pos_test_dirs, neg_dirs=neg_test_dirs, limit=limit)
        X_train, y_train = X, y
        if X_test.shape[0] == 0:
            raise SystemExit(f'No test samples found in provided test dirs: pos_test_dirs={pos_test_dirs} neg_test_dirs={neg_test_dirs}')
    else:
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
    parser.add_argument('--pos-train', nargs='+', type=Path, default=None, help='Positive class training directories (relative to --root or absolute)')
    parser.add_argument('--neg-train', nargs='+', type=Path, default=None, help='Negative class training directories')
    parser.add_argument('--pos-test', nargs='+', type=Path, default=None, help='Positive class test directories (optional)')
    parser.add_argument('--neg-test', nargs='+', type=Path, default=None, help='Negative class test directories (optional)')
    args = parser.parse_args()
    run(args.root, args.limit, args.model, args.out, pos_train_dirs=args.pos_train, neg_train_dirs=args.neg_train, pos_test_dirs=args.pos_test, neg_test_dirs=args.neg_test)
