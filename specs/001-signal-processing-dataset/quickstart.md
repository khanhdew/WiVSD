# Quickstart: CSI pipeline (signal processing + dataset)

## Prerequisites

- Python 3.11
- pip install -r requirements.txt (include numpy, pandas, scipy, scikit-learn, hampel, plotly)

## Run end-to-end pipeline

1. checkout branch: `git checkout 001-signal-processing-dataset`
2. ensure CSV path set in `csi_processing.ipynb` or CLI script input
3. run: `python -m src.csi_preprocessing.cli --input data/sample.csv --output out/dataset.npz --config config/default.yaml`

## Validate output

- `out/dataset.npz` should contain keys: `cnn_input_combined`, `breath_freqs`, `spec_times`.
- `out/dataset_quality.json` should contain `snr`, `spectral_entropy`, `outlier_rate`.

## Quick check

```bash
python -c "import numpy as np; d=np.load('out/dataset.npz'); print(d['cnn_input_combined'].shape)"
```
