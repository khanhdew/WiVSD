Short usage for precompute and training scripts

Purpose
- Precompute features once with `precompute_features.py` to avoid rerunning expensive Hampel processing during repeated training.

Precompute example
```
python scripts/precompute_features.py \
  --root . \
  --feature-cache /tmp/wivsd_feature_cache \
  --pos-dirs Router \
  --neg-dirs "router no person" \
  --limit 100 \
  --n-jobs 4
```

Train using cached features (reuse cache)
```
python scripts/train_ml_classifier.py \
  --root . \
  --feature-cache /tmp/wivsd_feature_cache \
  --no-tuning \
  --model-type gb \
  --out /tmp/train_report.json \
  --model /tmp/model.joblib
```

Run precompute step via the train script (alias)
```
python scripts/train_ml_classifier.py \
  --root . \
  --feature-cache /tmp/wivsd_feature_cache \
  --precompute-only \
  --no-tuning
```

Makefile snippet (optional)
```
precompute:
	python scripts/precompute_features.py --root . --feature-cache /tmp/wivsd_feature_cache --n-jobs 8

train:
	python scripts/train_ml_classifier.py --root . --feature-cache /tmp/wivsd_feature_cache --no-tuning --model-type gb --out /tmp/report.json --model /tmp/model.joblib
```

Notes
- `--feature-cache` must point to a writable directory. Cache entries are `.npz` + `.json` files keyed by a SHA1 of path|mtime_ns|size.
- Adjust `--n-jobs` to the number of CPU cores for faster preprocessing.
