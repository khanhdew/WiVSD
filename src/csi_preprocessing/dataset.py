import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

import numpy as np
import pandas as pd
from scipy.signal import spectrogram

from csi_preprocessing.parse import load_csi_csv
from csi_preprocessing.filters import apply_hampel, apply_savgol, elliptic_bandpass
from csi_preprocessing.pca import pca_reduce, select_pca_components


@dataclass
class NoiseFilterConfig:
    hampel_window_amp: int = 7
    hampel_sigma_amp: float = 3.0
    hampel_window_phs: int = 7
    hampel_sigma_phs: float = 3.0
    sg_window_amp: int = 11
    sg_polyorder_amp: int = 2
    sg_window_phs: int = 11
    sg_polyorder_phs: int = 2
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


def construct_matrix(ts_all, key: str) -> np.ndarray:
    if not ts_all:
        return np.zeros((0, 0))
    n_packets = max(len(df) for df in ts_all.values())
    n_subcarriers = len(ts_all)
    matrix = np.zeros((n_packets, n_subcarriers), dtype=float)
    for j, sub in enumerate(sorted(ts_all.keys())):
        values = ts_all[sub].get(key)
        if values is None:
            continue
        arr = np.asarray(values)
        matrix[: len(arr), j] = arr
    return matrix


def build_cnn_input(pca_matrix: np.ndarray, fs: float = 100.0, nperseg: int = 128, noverlap: int = 120) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if pca_matrix.size == 0:
        return np.zeros((0, 0, 0)), np.zeros(0), np.zeros(0)

    spec_stack = []
    freqs = None
    times = None

    for i in range(min(5, pca_matrix.shape[1])):
        series = np.asarray(pca_matrix[:, i])
        if series.size == 0:
            continue

        seg = min(nperseg, series.size)
        if seg < 2:
            continue
        overlap = min(noverlap, seg - 1)
        f, t, Sxx = spectrogram(series, fs=fs, window='hann', nperseg=seg, noverlap=overlap, scaling='density')

        if freqs is None:
            freqs = f
            times = t

        spec_stack.append(10 * np.log10(np.maximum(Sxx, 1e-12)))

    if not spec_stack:
        return np.zeros((0, 0, 0)), np.zeros(0), np.zeros(0)

    cnn_input = np.stack(spec_stack, axis=0)
    return cnn_input, freqs, times


def compute_outlier_rate(series: np.ndarray, threshold: float = 3.0) -> float:
    if series.size == 0:
        return 0.0
    mu = np.mean(series)
    sigma = np.std(series)
    if sigma == 0:
        return 0.0
    return float(np.sum(np.abs(series - mu) > threshold * sigma) / series.size)


def compute_snr(series: np.ndarray, noise_series: np.ndarray) -> float:
    if series.size == 0 or noise_series.size == 0 or noise_series.shape != series.shape:
        return 0.0
    signal_power = np.mean(series**2)
    noise_power = np.mean((series - noise_series)**2)
    if noise_power <= 0:
        return float('inf')
    return float(10 * np.log10(signal_power / noise_power))


def spectral_entropy(series: np.ndarray, n_bins: int = 128) -> float:
    if series.size == 0:
        return 0.0
    hist, _ = np.histogram(series, bins=n_bins, density=True)
    probs = hist.astype(np.float64)
    probs = probs[probs > 0]
    if probs.size == 0:
        return 0.0
    probs = probs / np.sum(probs)
    ent = -np.sum(probs * np.log2(probs))
    max_ent = np.log2(n_bins)
    return float(ent / max_ent) if max_ent > 0 else 0.0


def generate_quality_report(ts_all: dict) -> Dict[str, Any]:
    if not ts_all:
        return {'outlier_rate': 0.0, 'snr': 0.0}
    amp_rates = []
    phase_rates = []
    amp_snr = []
    phase_snr = []
    for df in ts_all.values():
        if 'amp_ellip' in df and 'amp_sg' in df:
            if df['amp_ellip'].size:
                amp_rates.append(compute_outlier_rate(df['amp_ellip'].values))
                amp_snr.append(compute_snr(df['amp_ellip'].values, df['amp_sg'].values))
        if 'phase_ellip' in df and 'phase_sg' in df:
            if df['phase_ellip'].size:
                phase_rates.append(compute_outlier_rate(df['phase_ellip'].values))
                phase_snr.append(compute_snr(df['phase_ellip'].values, df['phase_sg'].values))
    amp_entropy = []
    phase_entropy = []
    for df in ts_all.values():
        if 'amp_ellip' in df and df['amp_ellip'].size:
            amp_entropy.append(spectral_entropy(df['amp_ellip'].values))
        if 'phase_ellip' in df and df['phase_ellip'].size:
            phase_entropy.append(spectral_entropy(df['phase_ellip'].values))

    return {
        'outlier_rate_amp': float(np.mean(amp_rates)) if amp_rates else 0.0,
        'outlier_rate_phase': float(np.mean(phase_rates)) if phase_rates else 0.0,
        'snr_amp': float(np.mean(amp_snr)) if amp_snr else 0.0,
        'snr_phase': float(np.mean(phase_snr)) if phase_snr else 0.0,
        'entropy_amp': float(np.mean(amp_entropy)) if amp_entropy else 0.0,
        'entropy_phase': float(np.mean(phase_entropy)) if phase_entropy else 0.0,
    }


def save_dataset(output_dir: Path, cnn_input: np.ndarray, freq: np.ndarray, times: np.ndarray, quality: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_dir / 'dataset.npz', cnn_input=cnn_input, freq=freq, times=times)
    with open(output_dir / 'dataset_quality.json', 'w', encoding='utf-8') as fp:
        json.dump(quality, fp, indent=2, ensure_ascii=False)


def preprocess_csv_pipeline(csv_path: Path, output_dir: Path, fs: float = 100.0, config: Optional[NoiseFilterConfig] = None) -> Dict[str, Any]:
    if config is None:
        config = NoiseFilterConfig()

    df = load_csi_csv(csv_path)

    ts_all = {}
    for idx, row in df.iterrows():
        ts_all[idx] = pd.DataFrame({'amp': row['amplitude'], 'phase': row['phase']})

    for idx, df_sub in ts_all.items():
        df_sub['amp_hampel'] = apply_hampel(df_sub['amp'].values, window_size=config.hampel_window_amp, n_sigma=config.hampel_sigma_amp)
        df_sub['phase_hampel'] = apply_hampel(df_sub['phase'].values, window_size=config.hampel_window_phs, n_sigma=config.hampel_sigma_phs)
        df_sub['amp_sg'] = apply_savgol(df_sub['amp_hampel'].values, window_length=config.sg_window_amp, polyorder=config.sg_polyorder_amp)
        df_sub['phase_sg'] = apply_savgol(df_sub['phase_hampel'].values, window_length=config.sg_window_phs, polyorder=config.sg_polyorder_phs)
        df_sub['amp_ellip'] = elliptic_bandpass(df_sub['amp_sg'].values, fs=fs, lowcut=config.elliptic_low_amp, highcut=config.elliptic_high_amp, order=config.elliptic_order_amp, rp=config.elliptic_rp_amp, rs=config.elliptic_rs_amp)
        df_sub['phase_ellip'] = elliptic_bandpass(df_sub['phase_sg'].values, fs=fs, lowcut=config.elliptic_low_phs, highcut=config.elliptic_high_phs, order=config.elliptic_order_phs, rp=config.elliptic_rp_phs, rs=config.elliptic_rs_phs)

    amp_mat = construct_matrix(ts_all, 'amp_ellip')
    phase_mat = construct_matrix(ts_all, 'phase_ellip')

    amp_pca, amp_model = pca_reduce(amp_mat, n_components=min(5, amp_mat.shape[1] if amp_mat.ndim == 2 else 1))
    phase_pca, phase_model = pca_reduce(phase_mat, n_components=min(5, phase_mat.shape[1] if phase_mat.ndim == 2 else 1))

    amp_indices = select_pca_components(amp_model, min_cumulative_variance=0.8, max_components=5)
    phase_indices = select_pca_components(phase_model, min_cumulative_variance=0.8, max_components=5)

    amp_selected = amp_pca[:, amp_indices] if len(amp_indices) and amp_pca.size else np.zeros((amp_pca.shape[0], 0))
    phase_selected = phase_pca[:, phase_indices] if len(phase_indices) and phase_pca.size else np.zeros((phase_pca.shape[0], 0))

    cnn_input_amp, freqs_amp, times_amp = build_cnn_input(amp_selected, fs=fs)
    cnn_input_phase, freqs_phase, times_phase = build_cnn_input(phase_selected, fs=fs)

    cnn_input = np.concatenate([cnn_input_amp, cnn_input_phase], axis=0) if cnn_input_amp.size and cnn_input_phase.size else np.zeros((0, 0, 0))
    quality = generate_quality_report(ts_all)
    quality.update({
        'pca_amp_variance': amp_model.explained_variance_ratio_.tolist() if amp_model is not None else [],
        'pca_phase_variance': phase_model.explained_variance_ratio_.tolist() if phase_model is not None else [],
        'pca_amp_selected': len(amp_indices),
        'pca_phase_selected': len(phase_indices),
        'records': len(df),
    })

    save_dataset(output_dir, cnn_input, freqs_amp if freqs_amp is not None else np.array([]), times_amp if times_amp is not None else np.array([]), quality)

    return {'output': str(output_dir), 'quality': quality}
