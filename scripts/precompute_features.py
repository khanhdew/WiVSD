"""Precompute and cache features for CSV files using the project's preprocessing pipeline.

Saves per-file cache entries compatible with train_ml_classifier.py's cache format.
"""
from pathlib import Path
import argparse
import tempfile
import json
import hashlib
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

# Ensure local src/ is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / 'src'
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csi_preprocessing.dataset import preprocess_csv_pipeline


def _safe_cache_key(csv_path: Path, root: Path) -> str:
    try:
        rel_path = str(csv_path.relative_to(root))
    except Exception:
        rel_path = str(csv_path)
    stat = csv_path.stat()
    payload = f'{rel_path}|{stat.st_mtime_ns}|{stat.st_size}'.encode('utf-8')
    return hashlib.sha1(payload).hexdigest()


def _cache_paths(cache_dir: Path, cache_key: str):
    return cache_dir / f'{cache_key}.npz', cache_dir / f'{cache_key}.json'


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


def _build_pca_feature_vector(pca_matrix: np.ndarray, variance_ratio: np.ndarray, max_components: int = 5):
    features = []
    if pca_matrix is None or getattr(pca_matrix, 'size', 0) == 0:
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


def _process_csv_to_cache(csv_path: Path, label: int, root: Path, cache_dir: Path):
    # Run full preprocessing pipeline (Hampel, SG, elliptic, PCA)
    print(f'[precompute] start {csv_path}', flush=True)
    try:
        with tempfile.TemporaryDirectory() as td:
            result = preprocess_csv_pipeline(csv_path, Path(td))
    except Exception as e:
        print(f'[precompute] error {csv_path}: {e}', flush=True)
        return {'path': str(csv_path), 'error': str(e)}

    artifacts = result.get('artifacts', {}) if isinstance(result, dict) else {}
    amp_pca = artifacts.get('amp_pca')
    amp_var = np.asarray(artifacts.get('amp_pca_variance_ratio', []), dtype=float)
    phase_pca = artifacts.get('phase_pca')
    phs_var = np.asarray(artifacts.get('phase_pca_variance_ratio', []), dtype=float)

    amp_features = _build_pca_feature_vector(amp_pca, amp_var, max_components=5)
    phase_features = _build_pca_feature_vector(phase_pca, phs_var, max_components=5)
    features = amp_features + phase_features

    details = {
        'path': str(csv_path),
        'label': int(label),
        'quality': result.get('quality', {}),
        'pca_shape_amp': tuple(amp_pca.shape) if amp_pca is not None else None,
        'pca_shape_phase': tuple(phase_pca.shape) if phase_pca is not None else None,
        'pipeline': 'hampel -> savitzky-golay -> elliptic -> pca',
    }

    try:
        _save_cached_feature(cache_dir, csv_path, root, features, int(label), details)
    except Exception as e:
        print(f'[precompute] cache save failed {csv_path}: {e}', flush=True)
        return {'path': str(csv_path), 'error': f'cache_save_failed: {e}'}

    print(f'[precompute] done {csv_path}', flush=True)
    return {'path': str(csv_path), 'cached': True}


def find_csvs(root: Path, subdir: str):
    d = root / subdir
    if not d.exists():
        return []
    return sorted([p for p in d.rglob('*.csv')])


def main(root: Path, cache_dir: Path, pos_dirs: list, neg_dirs: list, limit: int = None, n_jobs: int = 4):
    root = Path(root)
    cache_dir = Path(cache_dir)
    tasks = []
    if not pos_dirs and not neg_dirs:
        pos_dirs = ['Router']
        neg_dirs = ['router no person']

    for d in pos_dirs:
        csvs = find_csvs(root, d)
        if limit:
            csvs = csvs[:limit]
        tasks.extend([(c, 1) for c in csvs])

    for d in neg_dirs:
        csvs = find_csvs(root, d)
        if limit:
            csvs = csvs[:limit]
        tasks.extend([(c, 0) for c in csvs])

    total = len(tasks)
    if total == 0:
        print('Precompute done: total=0, cached=0, errors=0')
        return

    results = []
    finished = 0
    print(f'[precompute] queued {total} csv files (n_jobs={n_jobs})', flush=True)
    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        future_map = {
            executor.submit(_process_csv_to_cache, c, lbl, root, cache_dir): (c, lbl)
            for c, lbl in tasks
        }
        for future in as_completed(future_map):
            item = future_map[future]
            finished += 1
            try:
                result = future.result()
            except Exception as e:
                result = {'path': str(item[0]), 'error': str(e)}
            results.append(result)
            status = 'cached' if result.get('cached') else 'error'
            print(f'[precompute] progress {finished}/{total} {status}: {item[0]}', flush=True)

    hits = sum(1 for r in results if r.get('cached'))
    errors = [r for r in results if r.get('error')]
    print(f'Precompute done: total={len(tasks)}, cached={hits}, errors={len(errors)}')
    if errors:
        print('Some errors:')
        for e in errors[:10]:
            print(' ', e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--feature-cache', type=Path, required=True)
    parser.add_argument('--pos-dirs', nargs='+', type=str, default=None)
    parser.add_argument('--neg-dirs', nargs='+', type=str, default=None)
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--n-jobs', type=int, default=4)
    args = parser.parse_args()
    main(args.root, args.feature_cache, args.pos_dirs, args.neg_dirs, limit=args.limit, n_jobs=args.n_jobs)
