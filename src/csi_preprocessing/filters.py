from typing import List

import numpy as np
from scipy.signal import ellip, sosfiltfilt, savgol_filter


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


def apply_hampel(data: np.ndarray, window_size: int, n_sigma: float) -> np.ndarray:
    from hampel import hampel

    if len(data) == 0:
        return data
    window_size = max(1, window_size)
    padded = np.pad(data, (window_size, window_size), mode='reflect')
    res = hampel(padded, window_size=window_size, n_sigma=n_sigma)
    return res.filtered_data[window_size:-window_size]


def apply_savgol(data: np.ndarray, window_length: int, polyorder: int) -> np.ndarray:
    if len(data) == 0:
        return data
    if window_length < polyorder + 2:
        window_length = polyorder + 2
    if window_length % 2 == 0:
        window_length += 1
    window_length = min(window_length, len(data) if len(data) % 2 == 1 else len(data) - 1)
    if window_length < polyorder + 1:
        return data
    return savgol_filter(data, window_length, polyorder)


def elliptic_bandpass(data: np.ndarray, fs: float, lowcut: float, highcut: float, order: int, rp: float, rs: float) -> np.ndarray:
    if len(data) == 0:
        return data
    nyq = fs / 2
    if lowcut <= 0 or highcut >= nyq or lowcut >= highcut:
        raise ValueError('Invalid bandpass frequencies')
    sos = ellip(order, rp, rs, [lowcut / nyq, highcut / nyq], btype='bandpass', output='sos')
    padlen = min(3000, len(data) - 1)
    return sosfiltfilt(sos, data, padlen=padlen)
