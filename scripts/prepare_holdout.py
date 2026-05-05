#!/usr/bin/env python3
"""Prepare holdout and temporary training dirs by copying CSVs.

Usage example:
  python scripts/prepare_holdout.py --root . --pos-dir Router --neg-dir "router no person" --holdout-dir holdout --train-tmp tmp_train --fraction 0.2 --seed 42
"""
from pathlib import Path
import argparse
import random
import shutil


def gather_csvs(src: Path):
    if not src.exists():
        return []
    # Search recursively so CSVs inside nested experiment subfolders are included
    return sorted([p for p in src.rglob('*.csv')])


def copy_split(src: Path, out_train: Path, out_hold: Path, fraction: float, seed: int):
    files = gather_csvs(src)
    out_train.mkdir(parents=True, exist_ok=True)
    out_hold.mkdir(parents=True, exist_ok=True)
    n = len(files)
    if n == 0:
        print(f'No CSVs in {src} (skipping)')
        return 0, 0
    k = max(1, int(n * fraction))
    k = min(k, n)
    rnd = random.Random(seed)
    holdout = set(rnd.sample(files, k))
    for f in files:
        dst = out_hold if f in holdout else out_train
        shutil.copy2(f, dst / f.name)
    return len(files) - len(holdout), len(holdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--pos-dir', type=str, default='Router')
    parser.add_argument('--neg-dir', type=str, default='router no person')
    parser.add_argument('--holdout-dir', type=str, default='holdout')
    parser.add_argument('--train-tmp', type=str, default='tmp_train')
    parser.add_argument('--fraction', type=float, default=0.2)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    root = args.root
    pos_src = root / args.pos_dir
    neg_src = root / args.neg_dir

    pos_train = root / args.train_tmp / args.pos_dir
    neg_train = root / args.train_tmp / args.neg_dir
    pos_hold = root / args.holdout_dir / args.pos_dir
    neg_hold = root / args.holdout_dir / args.neg_dir

    print('Preparing holdout/training dirs')
    tpos, hpos = copy_split(pos_src, pos_train, pos_hold, args.fraction, args.seed)
    tneg, hneg = copy_split(neg_src, neg_train, neg_hold, args.fraction, args.seed)

    print('\nSummary:')
    print(f'  pos: train={tpos} holdout={hpos} (from {pos_src})')
    print(f'  neg: train={tneg} holdout={hneg} (from {neg_src})')


if __name__ == '__main__':
    main()
