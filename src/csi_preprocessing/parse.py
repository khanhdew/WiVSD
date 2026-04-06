import json
from pathlib import Path
from typing import Any, Tuple

import numpy as np
import pandas as pd


def parse_csi_row(value: Any) -> np.ndarray:
    if pd.isna(value):
        return np.array([], dtype=np.float64)
    if isinstance(value, (list, tuple, np.ndarray)):
        return np.asarray(value, dtype=np.float64)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return np.array([], dtype=np.float64)
    try:
        return np.asarray(json.loads(value), dtype=np.float64)
    except Exception:
        try:
            tokens = [float(x) for x in value.replace('[', '').replace(']', '').split(',') if x.strip()]
            return np.asarray(tokens, dtype=np.float64)
        except Exception:
            return np.array([], dtype=np.float64)


def compute_amplitude_phase(csi_raw: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if csi_raw.size < 2:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    imag = csi_raw[0::2]
    real = csi_raw[1::2]
    l = min(len(real), len(imag))
    real = real[:l]
    imag = imag[:l]
    amp = np.hypot(real, imag)
    ph = np.arctan2(imag, real)
    return amp, ph


def load_csi_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if 'data' not in df.columns:
        raise ValueError('CSV missing `data` column')

    parsed = []
    for _, row in df.iterrows():
        csi_raw = parse_csi_row(row['data'])
        if csi_raw.size == 0 and str(row['data']).strip() != '':
            continue
        amp, ph = compute_amplitude_phase(csi_raw)
        parsed.append({'raw': csi_raw, 'amplitude': amp, 'phase': ph})

    parsed_df = pd.DataFrame(parsed)
    # If there are no valid parsed rows, return an empty DataFrame.
    # Callers (e.g., preprocess pipeline) handle empty dataframes gracefully.
    return parsed_df
