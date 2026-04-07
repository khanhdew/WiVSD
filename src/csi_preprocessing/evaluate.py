"""Evaluator for quick person/no-person runs over exported datasets or raw CSVs.

Usage (from repository root):

    PYTHONPATH=src python -m csi_preprocessing.evaluate --root /path/to/data --out reports/eval_summary.json

Behavior:
- Walks `--root` for `dataset.npz` files or CSV files under directories whose names contain
  "router" or "no person" (case-insensitive).
- If a `dataset_quality.json` file is present next to a `dataset.npz`, uses it.
- Otherwise the evaluator will run `preprocess_csv_pipeline` on CSV inputs to produce a dataset
  and then classify it.
- Infers ground-truth from parent directories: if any path component contains "no person" -> 0,
  else if it contains "router" -> 1, otherwise sample is skipped.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import tempfile
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from .classifier import predict_from_npz, predict_with_model_from_csv
from .dataset import preprocess_csv_pipeline
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import os


def infer_label_from_path(p: Path) -> Optional[int]:
    for part in p.parts:
        lp = part.lower()
        if 'no person' in lp or 'noperson' in lp:
            return 0
        if 'router no person' in lp:
            return 0
        if 'router' in lp:
            return 1
    return None


def find_candidate_npzs(root: Path) -> List[Path]:
    npzs = list(root.rglob('dataset.npz'))
    return npzs


def find_candidate_csvs(root: Path) -> List[Path]:
    return [p for p in root.rglob('*.csv') if any(('router' in part.lower() or 'no person' in part.lower()) for part in p.parts)]


def _process_npz_worker(npz_path_str: str, model_path_str: Optional[str] = None, threshold: float = 0.25) -> Optional[Dict[str, Any]]:
    npz_path = Path(npz_path_str)
    try:
        gt = infer_label_from_path(npz_path)
        if gt is None:
            gt = infer_label_from_path(npz_path.parent)
        if gt is None:
            return None

        # If a trained model is provided, try to find a CSV in same dir to compute features
        if model_path_str:
            try:
                csvs = list(npz_path.parent.glob('*.csv'))
                if csvs:
                    # prefer first CSV found
                    pred, details = predict_with_model_from_csv(csvs[0], model_path=model_path_str)
                    # If model returned probabilities, apply threshold to decide final prediction
                    prob = None
                    if isinstance(details, dict) and 'proba' in details:
                        try:
                            prob = float(details['proba'][0][1])
                        except Exception:
                            prob = None
                    if prob is not None:
                        final_pred = 1 if prob >= float(threshold) else 0
                        details['used_threshold'] = float(threshold)
                        details['proba_used'] = prob
                        return {'path': str(npz_path), 'ground_truth': int(gt), 'prediction': int(final_pred), 'details': details}
                    return {'path': str(npz_path), 'ground_truth': int(gt), 'prediction': int(pred) if pred is not None else None, 'details': details}
            except Exception:
                # fall back to NPZ-based prediction
                pass

        pred, details = predict_from_npz(npz_path)
        return {'path': str(npz_path), 'ground_truth': int(gt), 'prediction': int(pred) if pred is not None else None, 'details': details}
    except Exception as e:
        return {'path': str(npz_path), 'ground_truth': None, 'prediction': None, 'error': str(e)}


def _process_csv_worker(csv_path_str: str, model_path_str: Optional[str] = None, threshold: float = 0.25) -> Optional[Dict[str, Any]]:
    csv_path = Path(csv_path_str)
    try:
        gt = infer_label_from_path(csv_path)
        if gt is None:
            gt = infer_label_from_path(csv_path.parent)
        if gt is None:
            return None

        # If model provided, predict directly from CSV features
        if model_path_str:
            try:
                pred, details = predict_with_model_from_csv(csv_path, model_path=model_path_str)
                prob = None
                if isinstance(details, dict) and 'proba' in details:
                    try:
                        prob = float(details['proba'][0][1])
                    except Exception:
                        prob = None
                if prob is not None:
                    final_pred = 1 if prob >= float(threshold) else 0
                    details['used_threshold'] = float(threshold)
                    details['proba_used'] = prob
                    return {'path': str(csv_path), 'ground_truth': int(gt), 'prediction': int(final_pred), 'details': details}
                return {'path': str(csv_path), 'ground_truth': int(gt), 'prediction': int(pred) if pred is not None else None, 'details': details}
            except Exception:
                # fall back to preprocessing + NPZ prediction
                pass

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / (csv_path.stem + '_out')
            try:
                preprocess_csv_pipeline(csv_path, out_dir)
            except Exception as e:
                return {'path': str(csv_path), 'ground_truth': int(gt), 'prediction': None, 'error': str(e)}
            npz_path = out_dir / 'dataset.npz'
            if not npz_path.exists():
                return {'path': str(csv_path), 'ground_truth': int(gt), 'prediction': None, 'error': 'no_npz'}
            pred, details = predict_from_npz(npz_path)
            return {'path': str(csv_path), 'ground_truth': int(gt), 'prediction': int(pred) if pred is not None else None, 'details': details}
    except Exception as e:
        return {'path': str(csv_path), 'ground_truth': None, 'prediction': None, 'error': str(e)}


def evaluate(root: Path, save_json: Optional[Path] = None, jobs: Optional[int] = None, realtime: bool = True, model_path: Optional[str] = None, search_roots: Optional[List[Path]] = None, explicit_dirs: bool = False, threshold: float = 0.25) -> Dict[str, Any]:
    root = Path(root)
    results: List[Dict[str, Any]] = []

    # Determine which roots to search. If `search_roots` provided, use those
    # (this enables explicit directory evaluation). Otherwise use the single `root`.
    search_roots = [Path(r) for r in (search_roots or [root])]

    # First use existing NPZ outputs found under the chosen roots
    npzs: List[Path] = []
    csvs: List[Path] = []
    for sr in search_roots:
        npzs.extend(find_candidate_npzs(sr))
        if explicit_dirs:
            # Explicit directories: only accept exported CSV names to avoid example/test CSVs
            csvs.extend(list(sr.rglob('csi_data_*.csv')))
            csvs.extend(list(sr.rglob('csi_output.csv')))
        else:
            csvs.extend(find_candidate_csvs(sr))

    # Map to avoid double-processing: prefer npz if exists in same dir
    csv_to_process = []
    npz_dirs = {p.parent for p in npzs}

    for c in csvs:
        if c.parent not in npz_dirs:
            csv_to_process.append(c)

    # Build task list: ('npz', path_str) or ('csv', path_str)
    tasks = [('npz', str(p)) for p in npzs] + [('csv', str(c)) for c in csv_to_process]

    # Determine worker count
    if jobs is None:
        cpu = multiprocessing.cpu_count()
        workers = max(1, cpu - 1)
    elif jobs <= 0:
        workers = multiprocessing.cpu_count()
    else:
        workers = jobs

    total = len(tasks)
    if total == 0:
        # nothing to do
        summary = {
            'total_samples': 0,
            'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0,
            'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1': 0.0,
            'per_sample': []
        }
        if save_json:
            save_json.parent.mkdir(parents=True, exist_ok=True)
            save_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        return summary

    # Use a process pool and stream results as they complete for realtime logging
    if realtime:
        print(f'Running evaluation on {total} items using {workers} workers')

    # Determine model path: prefer CLI-provided `model_path`, otherwise try default artifact
    if model_path is None:
        try:
            default_model = Path('models') / 'rf_person_detector.joblib'
            if default_model.exists():
                model_path = str(default_model)
        except Exception:
            model_path = None

    with ProcessPoolExecutor(max_workers=workers) as exe:
        futures = {}
        for kind, path in tasks:
            if kind == 'npz':
                fut = exe.submit(_process_npz_worker, path, model_path_str=model_path, threshold=threshold)
            else:
                fut = exe.submit(_process_csv_worker, path, model_path_str=model_path, threshold=threshold)
            futures[fut] = path

        completed = 0
        for fut in as_completed(futures):
            res = fut.result()
            completed += 1
            if realtime:
                if res is None:
                    print(f'[{completed}/{total}] skipped: {futures[fut]}', flush=True)
                elif 'error' in res:
                    print(f'[{completed}/{total}] {res.get("path")} ERROR: {res.get("error")}', flush=True)
                else:
                    print(f'[{completed}/{total}] {res.get("path")} gt={res.get("ground_truth")} pred={res.get("prediction")}', flush=True)
            if res:
                results.append(res)

    # Compute metrics
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

    if save_json:
        save_json.parent.mkdir(parents=True, exist_ok=True)
        save_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    return summary


def main():
    parser = argparse.ArgumentParser(description='Evaluate heuristic person detector on dataset exports or CSVs')
    parser.add_argument('--root', required=True, type=Path, help='Root path to search for dataset exports or CSVs')
    parser.add_argument('--out', required=False, type=Path, help='Optional JSON summary output path')
    parser.add_argument('--jobs', '-j', type=int, default=None, help='Number of worker processes to use (default: auto)')
    parser.add_argument('--model', '--model-path', '--model_path', dest='model_path', required=False, default=None, help='Optional path to trained joblib model to prefer model predictions')
    parser.add_argument('--dirs', '-d', nargs='+', type=Path, dest='dirs', required=False, default=None, help='Explicit list of directories to evaluate (skips global scanning).')
    parser.add_argument('--no-realtime', action='store_true', help='Disable realtime progress logging')
    parser.add_argument('--threshold', type=float, default=0.25, help='Decision threshold for model probability to predict person (default: 0.25)')
    args = parser.parse_args()
    # If the caller specified explicit directories, forward them and set `explicit_dirs`.
    if args.dirs:
        summary = evaluate(args.root, save_json=args.out, jobs=args.jobs, realtime=(not args.no_realtime), model_path=args.model_path, search_roots=args.dirs, explicit_dirs=True, threshold=args.threshold)
    else:
        summary = evaluate(args.root, save_json=args.out, jobs=args.jobs, realtime=(not args.no_realtime), model_path=args.model_path, threshold=args.threshold)
    # print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
