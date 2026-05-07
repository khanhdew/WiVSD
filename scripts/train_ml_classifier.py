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
import tempfile
import sys
from typing import Optional
import re
import numpy as np
from tqdm import tqdm
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from joblib import dump, Parallel, delayed

# Ensure local src/ is importable when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / 'src'
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csi_preprocessing.dataset import preprocess_csv_pipeline


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


def _build_pipeline_feature_vector(quality: dict) -> list[float]:
    amp_var = list(quality.get('pca_amp_variance', []))
    phs_var = list(quality.get('pca_phase_variance', []))

    features = [
        float(quality.get('outlier_rate_amp', 0.0) or 0.0),
        float(quality.get('outlier_rate_phase', 0.0) or 0.0),
        float(quality.get('snr_amp', 0.0) or 0.0),
        float(quality.get('snr_phase', 0.0) or 0.0),
        float(quality.get('entropy_amp', 0.0) or 0.0),
        float(quality.get('entropy_phase', 0.0) or 0.0),
        float(quality.get('pca_amp_selected', 0.0) or 0.0),
        float(quality.get('pca_phase_selected', 0.0) or 0.0),
    ]

    for idx in range(5):
        features.append(float(amp_var[idx]) if idx < len(amp_var) else 0.0)
    for idx in range(5):
        features.append(float(phs_var[idx]) if idx < len(phs_var) else 0.0)

    return features


def _build_pca_feature_vector(pca_matrix: np.ndarray, variance_ratio: np.ndarray, max_components: int = 5) -> list[float]:
    features: list[float] = []
    if pca_matrix is None or pca_matrix.size == 0:
        for _ in range(max_components):
            features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
        return features

    n_components = min(max_components, pca_matrix.shape[1])
    for comp_idx in range(max_components):
        if comp_idx < n_components:
            series = np.asarray(pca_matrix[:, comp_idx], dtype=float)
            if series.size:
                features.extend([
                    float(np.mean(series)),
                    float(np.std(series)),
                    float(np.min(series)),
                    float(np.max(series)),
                    float(variance_ratio[comp_idx]) if comp_idx < len(variance_ratio) else 0.0,
                ])
            else:
                features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
    return features


def _extract_features_for_csv(c: Path, label: int, n_packets_max: int = 200):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = preprocess_csv_pipeline(c, Path(tmpdir))
    except Exception:
        return None
    quality = result.get('quality') if isinstance(result, dict) else None
    artifacts = result.get('artifacts') if isinstance(result, dict) else None
    if not isinstance(quality, dict):
        return None
    if quality.get('records', 0) == 0:
        return None
    if not isinstance(artifacts, dict):
        return None

    amp_features = _build_pca_feature_vector(
        artifacts.get('amp_pca'),
        np.asarray(artifacts.get('amp_pca_variance_ratio', []), dtype=float),
    )
    phase_features = _build_pca_feature_vector(
        artifacts.get('phase_pca'),
        np.asarray(artifacts.get('phase_pca_variance_ratio', []), dtype=float),
    )
    features = amp_features + phase_features
    details = {
        'path': str(c),
        'label': int(label),
        'quality': quality,
        'pca_shape_amp': tuple(artifacts['amp_pca'].shape) if artifacts.get('amp_pca') is not None else None,
        'pca_shape_phase': tuple(artifacts['phase_pca'].shape) if artifacts.get('phase_pca') is not None else None,
        'pipeline': 'hampel -> savitzky-golay -> elliptic -> pca',
    }
    return features, int(label), details


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
            print(f'[collect] label={label} subdir={subdir} csvs={len(csvs)}')
            results = Parallel(n_jobs=n_jobs, verbose=0)(
                delayed(_extract_features_for_csv)(c, label, n_packets_max) for c in tqdm(csvs, desc=f'Processing {subdir}')
            )
            for res in tqdm(results, desc=f'Collecting {subdir}', total=len(csvs), leave=False):
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
        print(f'[collect] pos_dirs={pos_dirs} pos_csvs={len(pos_csvs)}')
        print(f'[collect] neg_dirs={neg_dirs} neg_csvs={len(neg_csvs)}')

        print('[collect] Processing positive samples...')
        results_pos = Parallel(n_jobs=n_jobs, verbose=0)(
            delayed(_extract_features_for_csv)(c, 1, n_packets_max) for c in tqdm(pos_csvs, desc='Positive samples')
        )
        
        print('[collect] Processing negative samples...')
        results_neg = Parallel(n_jobs=n_jobs, verbose=0)(
            delayed(_extract_features_for_csv)(c, 0, n_packets_max) for c in tqdm(neg_csvs, desc='Negative samples')
        )

        all_results = results_pos + results_neg
        for res in tqdm(all_results, desc='Collecting features', total=len(all_results), leave=False):
            if not res:
                continue
            feat, lbl, det = res
            X.append(feat)
            y.append(lbl)
            details_list.append(det)
    return np.array(X), np.array(y), details_list


def run(root: Path, limit: int, model_out: Path, report_out: Path, pos_train_dirs: Optional[list] = None, neg_train_dirs: Optional[list] = None, pos_test_dirs: Optional[list] = None, neg_test_dirs: Optional[list] = None):
    # Collect training features
    print('[train] collecting training features...')
    X, y, details = collect_features(root, pos_dirs=pos_train_dirs, neg_dirs=neg_train_dirs, limit=limit)
    print(f'[train] X.shape={X.shape}, y.shape={y.shape}')
    if X.shape[0] < 10:
        raise SystemExit('Not enough samples to train (found {})'.format(X.shape[0]))

    # If explicit test dirs provided, collect test set from them, else split
    if pos_test_dirs or neg_test_dirs:
        print('[train] collecting explicit test features...')
        X_test, y_test, test_details = collect_features(root, pos_dirs=pos_test_dirs, neg_dirs=neg_test_dirs, limit=limit)
        X_train, y_train = X, y
        if X_test.shape[0] == 0:
            raise SystemExit(f'No test samples found in provided test dirs: pos_test_dirs={pos_test_dirs} neg_test_dirs={neg_test_dirs}')
    else:
        print('[train] splitting train/test...')
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print('[train] fitting model...')
    pipe = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1))
    pipe.fit(X_train, y_train)

    print('[train] evaluating...')
    y_pred = pipe.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary', zero_division=0)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    model_out.parent.mkdir(parents=True, exist_ok=True)
    dump(pipe, model_out)
    print(f'[train] model_saved={model_out}')

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
    print(f'[train] report_saved={report_out}')
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
