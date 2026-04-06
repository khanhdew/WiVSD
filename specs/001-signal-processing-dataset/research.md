# Research: CSI signal processing and stable dataset pipeline

## Decision: pipeline components
- Parse raw CSI JSON/binary into complex array for each packet.
- Compute amplitude and phase by converting (imag, real) pairs.
- Unwrap phase with numpy.unwrap per packet to avoid 2π jumps.
- Sanitize phase with linear detrend on valid subcarriers to remove SFO/CFO.
- Use Hampel filter (window=50 for amplitude, 30 for phase; n_sigma=3/2) to flag and suppress outliers.
- Smooth with Savitzky-Golay (window 31 amp, 41 phase, polyorder=3) for stable per-subcarrier signals.
- Apply elliptical bandpass on cleaned signals: amplitude 0.15-0.5Hz (order4), phase 0.1-0.6Hz (order2).
- Perform PCA top-5 on subcarriers (amplitude/phase) and select PCs with ≥80% cum. variance.
- Use STFT (nperseg=500, noverlap=450, hann) to produce spectrogram features for CNN tensor.
- Export artifacts as NPZ and JSON summary (traits, churn statistics, SNR, entropy, outlier rate).

## Rationale
- Process captured in notebook; chosen values are in experimental code and exhibit stable outputs.
- Aiming for reproducible research: explicit config and metadata in output.
- Support both training and inference-ready dataset (user choice B).

## Alternatives considered
- Wavelet denoising: rejected for added complexity and harder parameter control.
- Deep autoencoder denoising: rejected for heavy training demand; priority is simpler robust pipeline.

## Unknowns resolved
- Dataset artifact format: NPZ + JSON metadata for portability and easy re-load.
- Output ready for training + inference vs research only: both via standardized artifact.
