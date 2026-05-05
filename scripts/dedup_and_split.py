#!/usr/bin/env python3
"""Deduplicate CSV datasets and build train/holdout splits.

Usage example:
  python scripts/dedup_and_split.py --root . --pos-src Router --neg-src "router no person" \
    --train-tmp tmp_train --holdout holdout --fraction 0.2 --seed 42

The script:
 - Scans the source directories for CSV files
 - Deduplicates by SHA256 (keeps first occurrence)
 - Shuffles and splits unique files per class into train/holdout
 - Optionally moves duplicates to a separate folder or performs a dry-run
 - Writes a JSON report to `reports/rebuild_split_auto.json`
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


def sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as fh:
        for chunk in iter(lambda: fh.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def collect_csvs(src: Path) -> List[Path]:
    if not src.exists():
        return []
    return sorted([p for p in src.rglob('*.csv') if p.is_file()])


def dedupe_by_hash(paths: List[Path]) -> Tuple[Dict[str, Path], Dict[str, List[Path]]]:
    """Return (unique_map, duplicates_map).

    unique_map: hash -> first Path
    duplicates_map: hash -> list of duplicate Paths (including the first)
    """
    unique: Dict[str, Path] = {}
    dup: Dict[str, List[Path]] = {}
    for p in paths:
        try:
            h = sha256_of_file(p)
        except Exception:
            # skip unreadable files
            continue
        if h not in unique:
            unique[h] = p
            dup[h] = [p]
        else:
            dup[h].append(p)
    return unique, dup


def copy_split(unique_paths: List[Path], train_dir: Path, hold_dir: Path, fraction: float, seed: int, dry_run: bool = False):
    rng = random.Random(seed)
    paths = list(unique_paths)
    rng.shuffle(paths)
    k = max(1, int(len(paths) * fraction))
    hold_set = set(paths[:k])
    stats = {'total': len(paths), 'train': 0, 'holdout': 0}
    for p in paths:
        dst = hold_dir if p in hold_set else train_dir
        if not dry_run:
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst / p.name)
        if p in hold_set:
            stats['holdout'] += 1
        else:
            stats['train'] += 1
    return stats


def main():
    parser = argparse.ArgumentParser(description='Deduplicate CSVs and create train/holdout splits')
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--pos-src', type=Path, default=Path('Router'))
    parser.add_argument('--neg-src', type=Path, default=Path('router no person'))
    parser.add_argument('--train-tmp', type=Path, default=Path('tmp_train'))
    parser.add_argument('--holdout-dir', type=Path, default=Path('holdout'))
    parser.add_argument('--fraction', type=float, default=0.2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--duplicates-dir', type=Path, default=Path('data_duplicates'))
    parser.add_argument('--move-duplicates', action='store_true', help='Move duplicate files to --duplicates-dir (preserves originals)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--report', type=Path, default=Path('reports/rebuild_split_auto.json'))
    args = parser.parse_args()

    root = args.root
    pos_src = root / args.pos_src
    neg_src = root / args.neg_src
    train_tmp = root / args.train_tmp
    holdout = root / args.holdout_dir
    duplicates_dir = root / args.duplicates_dir

    # Prepare output dirs (don't delete existing contents unless copying)
    if not args.dry_run:
        (train_tmp / args.pos_src).mkdir(parents=True, exist_ok=True)
        (train_tmp / args.neg_src).mkdir(parents=True, exist_ok=True)
        (holdout / args.pos_src).mkdir(parents=True, exist_ok=True)
        (holdout / args.neg_src).mkdir(parents=True, exist_ok=True)

    report: Dict[str, object] = {}

    # Process each class
    for class_name, src in (('pos', pos_src), ('neg', neg_src)):
        files = collect_csvs(src)
        unique_map, dup_map = dedupe_by_hash(files)
        unique_paths = [unique_map[h] for h in unique_map]

        # Copy/split
        train_dir = train_tmp / src.name
        hold_dir = holdout / src.name
        stats = copy_split(unique_paths, train_dir, hold_dir, args.fraction, args.seed, dry_run=args.dry_run)

        # Handle duplicates
        duplicate_groups = {h: [str(p) for p in paths] for h, paths in dup_map.items() if len(paths) > 1}
        if args.move_duplicates and not args.dry_run:
            for h, paths in duplicate_groups.items():
                target = duplicates_dir / src.name
                target.mkdir(parents=True, exist_ok=True)
                # move all duplicates except the first occurrence
                for p in paths[1:]:
                    try:
                        shutil.move(str(p), str(target / p.name))
                    except Exception:
                        pass

        report[src.name] = {
            'source_dir': str(src),
            'scanned': len(files),
            'unique': len(unique_map),
            'train': stats['train'],
            'holdout': stats['holdout'],
            'duplicate_groups': len(duplicate_groups),
            'duplicate_sample': {h: [str(p) for p in dup_map[h][:5]] for i, h in enumerate(list(duplicate_groups.keys())[:10])}
        }

    # Cross-class overlap check (hash-level)
    # Build map from hash->class occurrences
    all_hashes: Dict[str, List[str]] = {}
    for src in (pos_src, neg_src):
        for p in collect_csvs(src):
            try:
                h = sha256_of_file(p)
            except Exception:
                continue
            all_hashes.setdefault(h, []).append(str(p))
    overlaps = {h: paths for h, paths in all_hashes.items() if len({Path(x).parent.name for x in paths}) > 1}
    report['cross_class_overlaps'] = len(overlaps)
    report['cross_class_sample'] = {h: overlaps[h][:5] for i, h in enumerate(list(overlaps.keys())[:10])}

    # Save report
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically to avoid partial/truncated JSON on errors
    tmp = args.report.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as fo:
        json.dump(report, fo, indent=2, ensure_ascii=False)
    tmp.replace(args.report)

    print('Done. report written to', str(args.report))


if __name__ == '__main__':
    main()
