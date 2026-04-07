# Data Model: CSI processing pipeline

## Entities

- **CSIPacket**
  - timestamp: float
  - rssi: float
  - length: int
  - subcarrier_count: int
  - data_raw: list[float]

- **PreprocessedSeries**
  - packet_idx: int
  - amp: np.ndarray
  - phase: np.ndarray
  - phase_unwrapped: np.ndarray
  - phase_sanitized: np.ndarray
  - amp_hampel, phase_hampel: np.ndarray
  - amp_sg, phase_sg: np.ndarray
  - amp_ellip, phase_ellip: np.ndarray

- **NoiseFilterConfig**
  - hampl_window_amp, hampl_sigma_amp
  - hampl_window_phs, hampl_sigma_phs
  - sg_window_amp, sg_polyorder_amp
  - sg_window_phs, sg_polyorder_phs
  - elliptic_low_amp, elliptic_high_amp, elliptic_low_phs, elliptic_high_phs

- **DimReductionModel**
  - pca_amp, pca_phs objects
  - explained_variance_ratio_amp, explained_variance_ratio_phs

- **DatasetArtifact**
  - path: str
  - cnn_input_combined: ndarray (channels x freq x time)
  - quality_json: dict
  - metadata: dict
