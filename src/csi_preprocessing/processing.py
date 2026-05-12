import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.signal import ellip, sosfiltfilt, savgol_filter, spectrogram
from sklearn.decomposition import PCA
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except Exception:
    NUMBA_AVAILABLE = False
    def jit(*args, **kwargs):
        return lambda f: f


@dataclass
class NoiseFilterConfig:
    hampel_window_amp: int = 50
    hampel_sigma_amp: float = 3.0
    hampel_window_phs: int = 30
    hampel_sigma_phs: float = 2.0
    sg_window_amp: int = 31
    sg_polyorder_amp: int = 3
    sg_window_phs: int = 41
    sg_polyorder_phs: int = 3
    elliptic_low_amp: float = 0.15
    elliptic_high_amp: float = 0.5
    elliptic_order_amp: int = 4
    elliptic_rp_amp: float = 0.1
    elliptic_rs_amp: float = 40
    elliptic_low_phs: float = 0.1
    elliptic_high_phs: float = 0.6
    elliptic_order_phs: int = 2
    elliptic_rp_phs: float = 0.5
    elliptic_rs_phs: float = 50


def parse_csi_row(value: Any) -> np.ndarray:
    if pd.isna(value):
        return np.array([], dtype=np.float64)
    if isinstance(value, list):
        return np.asarray(value, dtype=np.float64)
    try:
        return np.asarray(json.loads(value), dtype=np.float64)
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
    amp = np.sqrt(real**2 + imag**2)
    ph = np.arctan2(imag, real)
    return amp, ph


def unwrap_phase_list(phases: List[np.ndarray]) -> List[np.ndarray]:
    return [np.unwrap(p) if len(p) else p for p in phases]


def sanitize_phase_robust(phase_array: np.ndarray) -> np.ndarray:
    if len(phase_array) == 0:
        return phase_array
    valid_idx = np.where(np.abs(phase_array) > 1e-6)[0]
    if len(valid_idx) < 2:
        return phase_array
    x = valid_idx
    y = phase_array[valid_idx]
    a, b = np.polyfit(x, y, 1)
    sanitized = phase_array.copy()
    sanitized[valid_idx] = y - (a * x + b)
    return sanitized


@jit(nopython=True, cache=True, fastmath=True)
def _hampel_numba_impl(data: np.ndarray, window_size: int, n_sigma: float) -> np.ndarray:
    """Numba JIT-compiled Hampel filter for speed."""
    n = len(data)
    filtered = data.copy()
    half_window = window_size // 2
    
    for i in range(n):
        # Get window around current point
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        window = data[start:end]
        
        # Calculate median and MAD (median absolute deviation)
        median_val = np.median(window)
        mad = np.median(np.abs(window - median_val))
        
        # Detect and replace outliers
        threshold = n_sigma * mad
        if np.abs(data[i] - median_val) > threshold and mad > 0:
            filtered[i] = median_val
    
    return filtered


def apply_hampel(data: np.ndarray, window_size: int, n_sigma: float) -> np.ndarray:
    """Apply Hampel filter using Numba-compiled implementation."""
    if len(data) == 0:
        return data
    
    # Pad data to handle boundaries
    pad_len = window_size * 2
    padded = np.pad(data, (pad_len, pad_len), mode='reflect')
    
    # Apply Hampel filter
    filtered_padded = _hampel_numba_impl(padded, window_size, n_sigma)
    
    # Remove padding
    return filtered_padded[pad_len:-pad_len]


def apply_savgol(data: np.ndarray, window_length: int, polyorder: int) -> np.ndarray:
    if len(data) == 0:
        return data
    window_len = min(window_length, len(data) if len(data) % 2 else len(data) - 1)
    if window_len >= polyorder + 1:
        return savgol_filter(data, window_len, polyorder)
    return data


def elliptic_bandpass(data: np.ndarray, fs: float, lowcut: float, highcut: float, order: int, rp: float, rs: float) -> np.ndarray:
    if len(data) == 0:
        return data
    nyquist = fs / 2
    sos = ellip(N=order, rp=rp, rs=rs, Wn=[lowcut/nyquist, highcut/nyquist], btype='bandpass', output='sos')
    padlen = min(3000, len(data)-1)
    return sosfiltfilt(sos, data, padlen=padlen)


def construct_matrix(ts_all: Dict[int, pd.DataFrame], key: str) -> np.ndarray:
    if not ts_all:
        return np.zeros((0, 0))
    n_packets = max(len(df) for df in ts_all.values())
    n_sub = len(ts_all)
    M = np.zeros((n_packets, n_sub), dtype=float)
    for j, sub_idx in enumerate(sorted(ts_all.keys())):
        arr = ts_all[sub_idx][key].values
        M[:len(arr), j] = arr
    return M


def pca_reduce(matrix: np.ndarray, n_components: int = 5) -> Tuple[np.ndarray, PCA]:
    pca = PCA(n_components=n_components)
    trans = pca.fit_transform(matrix)
    return trans, pca


def save_dataset(output_dir: Path, cnn_input: np.ndarray, breath_freqs: np.ndarray, spec_times: np.ndarray, quality: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_dir / 'dataset.npz', cnn_input=cnn_input, breath_freqs=breath_freqs, spec_times=spec_times)
    with open(output_dir / 'dataset_quality.json', 'w', encoding='utf-8') as fp:
        json.dump(quality, fp, indent=2, ensure_ascii=False)


def do_full_pipeline(csv_path: Path, output_dir: Path, config: Optional[NoiseFilterConfig] = None) -> Dict[str, Any]:
    if config is None:
        config = NoiseFilterConfig()
    df = pd.read_csv(csv_path)
    df['csi_raw'] = df['data'].apply(parse_csi_row)
    df[['amplitude', 'phase']] = df['csi_raw'].apply(lambda x: pd.Series(compute_amplitude_phase(x)))

    df['phase_unwrapped'] = [np.unwrap(p) if len(p) else p for p in df['phase'].values]
    df['phase_sanitized'] = df['phase_unwrapped'].apply(sanitize_phase_robust)

    ts_all = {}
    for i, row in df.iterrows():
        ts_all[i] = pd.DataFrame({'amp': row['amplitude'], 'phase': row['phase_sanitized']})

    for sub_idx, df_sub in ts_all.items():
        ts_all[sub_idx]['amp_hampel'] = apply_hampel(df_sub['amp'].values, config.hampel_window_amp, config.hampel_sigma_amp)
        ts_all[sub_idx]['phase_hampel'] = apply_hampel(df_sub['phase'].values, config.hampel_window_phs, config.hampel_sigma_phs)
        ts_all[sub_idx]['amp_sg'] = apply_savgol(ts_all[sub_idx]['amp_hampel'].values, config.sg_window_amp, config.sg_polyorder_amp)
        ts_all[sub_idx]['phase_sg'] = apply_savgol(ts_all[sub_idx]['phase_hampel'].values, config.sg_window_phs, config.sg_polyorder_phs)
        ts_all[sub_idx]['amp_ellip'] = elliptic_bandpass(ts_all[sub_idx]['amp_sg'].values, 100.0, config.elliptic_low_amp, config.elliptic_high_amp, config.elliptic_order_amp, config.elliptic_rp_amp, config.elliptic_rs_amp)
        ts_all[sub_idx]['phase_ellip'] = elliptic_bandpass(ts_all[sub_idx]['phase_sg'].values, 100.0, config.elliptic_low_phs, config.elliptic_high_phs, config.elliptic_order_phs, config.elliptic_rp_phs, config.elliptic_rs_phs)

    amp_matrix = construct_matrix(ts_all, 'amp_ellip')
    phs_matrix = construct_matrix(ts_all, 'phase_ellip')

    amp_pca, pca_amp_model = pca_reduce(amp_matrix)
    phs_pca, pca_phs_model = pca_reduce(phs_matrix)

    freqs, times, spec_amp = zip(*[spectrogram(amp_pca[:, k], fs=100.0, window='hann', nperseg=500, noverlap=450, scaling='density') for k in range(amp_pca.shape[1])])
    breath_mask = (freqs[0] >= 0.1) & (freqs[0] <= 0.6)
    breath_freqs = freqs[0][breath_mask]
    breath_spec_amp = np.stack([s[breath_mask, :] for s in spec_amp], axis=0)

    breath_spec_amp_db = 10 * np.log10(np.maximum(breath_spec_amp, 1e-12))
    cnn_input_combined = np.concatenate([breath_spec_amp_db, breath_spec_amp_db], axis=0)

    quality = {
        'pca_amp_variance': pca_amp_model.explained_variance_ratio_.tolist(),
        'pca_phs_variance': pca_phs_model.explained_variance_ratio_.tolist(),
        'shape': cnn_input_combined.shape,
    }

    save_dataset(output_dir, cnn_input_combined, breath_freqs, times[0], quality)

    return {'quality': quality, 'output': str(output_dir)}
