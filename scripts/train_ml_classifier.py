"""Train an optimized ML classifier from CSV-derived features and save model+report.

Usage:
    python scripts/train_ml_classifier.py --root . --limit 200 --model models/rf_person_detector.joblib --out reports/model_train_eval.json

New options:
    --pos-train DIR [DIR ...]   directories (relative to --root or absolute) containing positive samples for training
    --neg-train DIR [DIR ...]   directories containing negative samples for training
    --pos-test DIR [DIR ...]    optional directories containing positive samples for testing (if provided, skip random split)
    --neg-test DIR [DIR ...]    optional directories containing negative samples for testing
    --model-type STR            'gb' (optimized, default), 'rf', default: gb
    --cv-folds INT              number of cross-validation folds, default: 5
    --no-tuning                 skip hyperparameter tuning
"""
from pathlib import Path
import argparse
import json
import tempfile
import sys
import hashlib
from typing import Optional
import re
import numpy as np
from tqdm import tqdm
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, roc_auc_score, confusion_matrix
from joblib import dump, Parallel, delayed
import warnings
warnings.filterwarnings('ignore')

# Ensure local src/ is importable when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / 'src'
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csi_preprocessing.dataset import preprocess_csv_pipeline


def _safe_cache_key(csv_path: Path, root: Path) -> str:
    rel_path = str(csv_path.relative_to(root)) if csv_path.is_relative_to(root) else str(csv_path)
    stat = csv_path.stat()
    payload = f'{rel_path}|{stat.st_mtime_ns}|{stat.st_size}'.encode('utf-8')
    return hashlib.sha1(payload).hexdigest()


def _cache_paths(cache_dir: Path, cache_key: str) -> tuple[Path, Path]:
    return cache_dir / f'{cache_key}.npz', cache_dir / f'{cache_key}.json'


def _load_cached_feature(cache_dir: Path, csv_path: Path, root: Path):
    cache_key = _safe_cache_key(csv_path, root)
    npz_path, meta_path = _cache_paths(cache_dir, cache_key)
    if not npz_path.exists() or not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
    except Exception:
        return None

    current_stat = csv_path.stat()
    if meta.get('mtime_ns') != current_stat.st_mtime_ns or meta.get('size') != current_stat.st_size:
        return None

    try:
        payload = np.load(npz_path, allow_pickle=True)
        features = payload['features'].astype(float).tolist()
        label = int(payload['label'])
        details = json.loads(str(payload['details'].item()))
        return features, label, details
    except Exception:
        return None


def _save_cached_feature(cache_dir: Path, csv_path: Path, root: Path, features, label: int, details: dict):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _safe_cache_key(csv_path, root)
    npz_path, meta_path = _cache_paths(cache_dir, cache_key)
    current_stat = csv_path.stat()
    np.savez_compressed(
        npz_path,
        features=np.asarray(features, dtype=np.float32),
        label=np.asarray(label, dtype=np.int64),
        details=np.asarray(json.dumps(details, ensure_ascii=False), dtype=object),
    )
    meta_path.write_text(json.dumps({
        'path': str(csv_path),
        'mtime_ns': current_stat.st_mtime_ns,
        'size': current_stat.st_size,
    }, indent=2), encoding='utf-8')


def _preprocess_or_load_feature(csv_path: Path, label: int, root: Path, cache_dir: Optional[Path], n_packets_max: int = 200):
    if cache_dir is not None:
        cached = _load_cached_feature(cache_dir, csv_path, root)
        if cached is not None:
            return cached, True

    result = _extract_features_for_csv(csv_path, label, n_packets_max)
    if result is None:
        return None

    features, lbl, details = result
    if cache_dir is not None:
        _save_cached_feature(cache_dir, csv_path, root, features, lbl, details)
    return (features, lbl, details), False


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


def collect_features(root: Path, pos_dirs: Optional[list] = None, neg_dirs: Optional[list] = None, limit: int = None, n_jobs: int = -1, n_packets_max: int = 200, cache_dir: Optional[Path] = None):
    """Collect features from directories.

    - If `pos_dirs`/`neg_dirs` are None, defaults to ['Router'] and ['router no person'] under `root`.
    - `pos_dirs` and `neg_dirs` are lists of Path or strings; non-absolute paths are resolved under `root`.
    - Returns (X, y, details_list)
    """
    root = Path(root)
    cache_dir = Path(cache_dir) if cache_dir is not None else None
    X = []
    y = []
    details_list = []
    cache_hits = 0
    cache_misses = 0

    if pos_dirs is None and neg_dirs is None:
        targets = [('Router', 1), ('router no person', 0)]
        for subdir, label in targets:
            csvs = find_csvs(root, subdir)
            if limit:
                csvs = csvs[:limit]
            print(f'[collect] label={label} subdir={subdir} csvs={len(csvs)}')
            results = Parallel(n_jobs=n_jobs, verbose=0)(
                delayed(_preprocess_or_load_feature)(c, label, root, cache_dir, n_packets_max) for c in tqdm(csvs, desc=f'Processing {subdir}')
            )
            for res in tqdm(results, desc=f'Collecting {subdir}', total=len(csvs), leave=False):
                if not res:
                    continue
                (feat, lbl, det), from_cache = res
                cache_hits += int(from_cache)
                cache_misses += int(not from_cache)
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
            delayed(_preprocess_or_load_feature)(c, 1, root, cache_dir, n_packets_max) for c in tqdm(pos_csvs, desc='Positive samples')
        )
        
        print('[collect] Processing negative samples...')
        results_neg = Parallel(n_jobs=n_jobs, verbose=0)(
            delayed(_preprocess_or_load_feature)(c, 0, root, cache_dir, n_packets_max) for c in tqdm(neg_csvs, desc='Negative samples')
        )

        all_results = results_pos + results_neg
        for res in tqdm(all_results, desc='Collecting features', total=len(all_results), leave=False):
            if not res:
                continue
            (feat, lbl, det), from_cache = res
            cache_hits += int(from_cache)
            cache_misses += int(not from_cache)
            X.append(feat)
            y.append(lbl)
            details_list.append(det)
    if cache_dir is not None:
        print(f'[collect] feature cache: hits={cache_hits} misses={cache_misses} cache_dir={cache_dir}')
    return np.array(X), np.array(y), details_list


def compute_sample_weights(y):
    """Return per-sample weights to balance the binary classes."""
    unique, counts = np.unique(y, return_counts=True)
    class_weights = {cls: len(y) / (2.0 * cnt) for cls, cnt in zip(unique, counts)}
    return np.asarray([class_weights[int(label)] for label in y], dtype=float)


def build_random_forest_optimized(enable_tuning: bool = True, cv_folds: int = 5) -> tuple:
    """Build optimized Random Forest pipeline with tuning."""
    if not enable_tuning:
        rf_clf = RandomForestClassifier(
            n_estimators=700,
            max_depth=10,
            min_samples_split=8,
            min_samples_leaf=3,
            max_features='sqrt',
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1,
            bootstrap=True
        )
        pipe = Pipeline([('classifier', rf_clf)])
        return pipe, None
    
    rf_base = RandomForestClassifier(
        random_state=42,
        n_jobs=-1,
        class_weight='balanced_subsample',
        bootstrap=True,
    )
    
    param_grid = {
        'classifier__n_estimators': [400, 700, 900],
        'classifier__max_depth': [8, 10, 12],
        'classifier__min_samples_split': [5, 8, 12],
        'classifier__min_samples_leaf': [2, 3, 5],
        'classifier__max_features': ['sqrt', 'log2'],
    }
    
    pipe_base = Pipeline([('classifier', rf_base)])
    
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    
    gs = GridSearchCV(
        pipe_base,
        param_grid,
        cv=cv,
        scoring='f1',
        n_jobs=-1,
        verbose=1,
        error_score=-1
    )
    return pipe_base, (gs, param_grid)


def build_gradient_boosting_pipeline(n_features: int, cv_folds: int = 5, enable_tuning: bool = True) -> tuple:
    """Build Gradient Boosting pipeline with optional hyperparameter tuning (OPTIMIZED)."""
    if not enable_tuning:
        gb_clf = GradientBoostingClassifier(
            n_estimators=700,
            max_depth=3,
            learning_rate=0.03,
            min_samples_split=8,
            min_samples_leaf=4,
            subsample=0.8,
            max_features='sqrt',
            random_state=42
        )
        pipe = Pipeline([('classifier', gb_clf)])
        return pipe, None
    
    gb_base = GradientBoostingClassifier(random_state=42)
    
    param_grid = {
        'classifier__n_estimators': [400, 700, 900],
        'classifier__max_depth': [2, 3, 4],
        'classifier__learning_rate': [0.01, 0.03, 0.05],
        'classifier__min_samples_split': [5, 8, 12],
        'classifier__min_samples_leaf': [2, 4, 6],
        'classifier__subsample': [0.7, 0.8, 0.9],
        'classifier__max_features': ['sqrt', 'log2'],
    }
    
    pipe_base = Pipeline([('classifier', gb_base)])
    
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    
    gs = GridSearchCV(
        pipe_base,
        param_grid,
        cv=cv,
        scoring='f1',
        n_jobs=-1,
        verbose=1,
        error_score=-1
    )
    return pipe_base, (gs, param_grid)


def analyze_feature_importance(pipe: Pipeline, n_features: int):
    """Extract and analyze feature importance from the model."""
    try:
        model = pipe.named_steps.get('classifier')
        
        if model and hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            print('\n[analysis] Top 15 feature importances:')
            for i in range(min(15, len(importances))):
                feat_idx = indices[i]
                print(f'  Feature {feat_idx}: {importances[feat_idx]:.6f}')
            
            return importances.tolist()
    except Exception as e:
        print(f'[warn] Could not extract feature importance: {e}')
    return None


def run(root: Path, limit: int, model_out: Path, report_out: Path, 
        pos_train_dirs: Optional[list] = None, neg_train_dirs: Optional[list] = None,
        pos_test_dirs: Optional[list] = None, neg_test_dirs: Optional[list] = None,
        model_type: str = 'gb', cv_folds: int = 5, no_tuning: bool = False,
        cache_dir: Optional[Path] = None, precompute_only: bool = False):
    # Collect training features
    print('[train] collecting training features...')
    X, y, details = collect_features(root, pos_dirs=pos_train_dirs, neg_dirs=neg_train_dirs, limit=limit, cache_dir=cache_dir)
    print(f'[train] X.shape={X.shape}, y.shape={y.shape}')
    if X.shape[0] < 10:
        raise SystemExit('Not enough samples to train (found {})'.format(X.shape[0]))

    if precompute_only:
        print(f'[train] precompute_only enabled; cached {X.shape[0]} samples to {cache_dir}')
        return {
            'mode': 'precompute_only',
            'n_samples': int(X.shape[0]),
            'n_features': int(X.shape[1]),
            'cache_dir': str(cache_dir) if cache_dir is not None else None,
        }

    # Check class balance
    unique, counts = np.unique(y, return_counts=True)
    print(f'[train] class distribution: {dict(zip(unique, counts))}')

    # If explicit test dirs provided, collect test set from them, else split
    if pos_test_dirs or neg_test_dirs:
        print('[train] collecting explicit test features...')
        X_test, y_test, test_details = collect_features(root, pos_dirs=pos_test_dirs, neg_dirs=neg_test_dirs, limit=limit, cache_dir=cache_dir)
        X_train, y_train = X, y
        if X_test.shape[0] == 0:
            raise SystemExit(f'No test samples found in provided test dirs: pos_test_dirs={pos_test_dirs} neg_test_dirs={neg_test_dirs}')
    else:
        print('[train] splitting train/test (80/20)...')
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f'[train] X_train.shape={X_train.shape}, X_test.shape={X_test.shape}')

    # Build and fit model
    print(f'[train] building {model_type} model with {"tuning" if not no_tuning else "no tuning"}...')
    
    if model_type.lower() == 'rf':
        pipe_base, gs_info = build_random_forest_optimized(enable_tuning=(not no_tuning), cv_folds=cv_folds)
    else:  # default to gb (gradient boosting)
        pipe_base, gs_info = build_gradient_boosting_pipeline(X_train.shape[1], cv_folds=cv_folds, enable_tuning=(not no_tuning))

    sample_weights = compute_sample_weights(y_train)

    if gs_info and not no_tuning:
        print('[train] running hyperparameter tuning with GridSearchCV...')
        gs, param_grid = gs_info
        gs.fit(X_train, y_train, classifier__sample_weight=sample_weights)
        pipe = gs.best_estimator_
        print(f'[train] best_params: {gs.best_params_}')
        print(f'[train] best_cv_score (F1): {gs.best_score_:.4f}')
    else:
        print('[train] fitting model without tuning...')
        pipe = pipe_base
        pipe.fit(X_train, y_train, classifier__sample_weight=sample_weights)

    print('[train] evaluating on test set...')
    y_pred = pipe.predict(X_test)
    y_pred_proba = pipe.predict_proba(X_test)[:, 1]
    
    acc = float(accuracy_score(y_test, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary', zero_division=0)
    
    # Calculate additional metrics
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    try:
        auc_score = float(roc_auc_score(y_test, y_pred_proba))
    except:
        auc_score = 0.0
    
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    
    # Extract feature importance
    feature_importance = analyze_feature_importance(pipe, X_train.shape[1])

    model_out.parent.mkdir(parents=True, exist_ok=True)
    dump(pipe, model_out)
    print(f'[train] model_saved={model_out}')

    # Prepare comprehensive report
    out = {
        'model_type': model_type,
        'model_version': 'optimized_v2',
        'n_samples': int(X.shape[0]),
        'n_features': int(X.shape[1]),
        'class_distribution': dict(zip(unique.tolist(), counts.tolist())),
        'train_size': int(X_train.shape[0]),
        'test_size': int(X_test.shape[0]),
        'metrics': {
            'accuracy': acc,
            'precision': float(prec),
            'recall': float(rec),
            'f1': float(f1),
            'specificity': specificity,
            'auc': auc_score,
            'tp': int(tp),
            'fp': int(fp),
            'tn': int(tn),
            'fn': int(fn),
        },
        'model_path': str(model_out),
        'report': report,
        'feature_importance': feature_importance,
        'cv_folds': cv_folds,
        'sample_details': details[:50]
    }
    
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(f'[train] report_saved={report_out}')
    
    print('\n' + '='*60)
    print('FINAL RESULTS:')
    print('='*60)
    print(f'Accuracy:   {acc:.4f}')
    print(f'Precision:  {prec:.4f}')
    print(f'Recall:     {rec:.4f}')
    print(f'F1-Score:   {f1:.4f}')
    print(f'Specificity: {specificity:.4f}')
    print(f'AUC:        {auc_score:.4f}')
    print(f'TP={tp}, FP={fp}, TN={tn}, FN={fn}')
    print('='*60 + '\n')
    
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train optimized ML classifier for person detection from CSI data')
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--model', type=Path, default=Path('models/rf_person_detector.joblib'))
    parser.add_argument('--out', type=Path, default=Path('reports/model_train_eval.json'))
    parser.add_argument('--pos-train', nargs='+', type=Path, default=None, help='Positive class training directories (relative to --root or absolute)')
    parser.add_argument('--neg-train', nargs='+', type=Path, default=None, help='Negative class training directories')
    parser.add_argument('--pos-test', nargs='+', type=Path, default=None, help='Positive class test directories (optional)')
    parser.add_argument('--neg-test', nargs='+', type=Path, default=None, help='Negative class test directories (optional)')
    parser.add_argument('--model-type', type=str, default='gb', choices=['gb', 'rf'], 
                        help='Model type: gb=GradientBoosting (default, optimized) or rf=RandomForest')
    parser.add_argument('--cv-folds', type=int, default=5, help='Number of cross-validation folds (default: 5)')
    parser.add_argument('--no-tuning', action='store_true', help='Skip hyperparameter tuning')
    parser.add_argument('--feature-cache', type=Path, default=None, help='Directory to store/load precomputed features')
    parser.add_argument('--precompute-only', action='store_true', help='Only preprocess and cache features, then exit')
    
    args = parser.parse_args()
    run(args.root, args.limit, args.model, args.out, 
        pos_train_dirs=args.pos_train, neg_train_dirs=args.neg_train,
        pos_test_dirs=args.pos_test, neg_test_dirs=args.neg_test,
        model_type=args.model_type, cv_folds=args.cv_folds, no_tuning=args.no_tuning,
        cache_dir=args.feature_cache, precompute_only=args.precompute_only)
