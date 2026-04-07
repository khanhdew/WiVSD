# Feature Specification: Signal-source signal processing and stable dataset pipeline

**Feature Branch**: `001-signal-processing-dataset`  
**Created**: 2026-03-29  
**Status**: Draft  
**Input**: User description: "tập trung vào các phần xử lý tín hiệu như lọc nhiễu, giảm chiều để làm sao cuối cùng có được bộ dữ liệu ổn nhất"

## Clarifications

### Session 2026-03-29

- Q: What is the target deployment form for the cleaned dataset artifact? → A: B (Dataset outputs targeted for both model training and inference pipelines)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean and normalize CSI feature stream (Priority: P1)

Researcher needs a reproducible pipeline that takes raw CSI packets and outputs per-frame, per-subcarrier amplitude/phase time-series with outlier removal and band-limited smoothing.

**Why this priority**: This is the foundation stage; without clean input, later dimensionality reduction and dataset stability are meaningless.

**Independent Test**: Run the preprocessing script on a raw CSI file and verify output metrics.

**Acceptance Scenarios**:
1. **Given** a raw CSI CSV with binary or JSON data payloads, **When** the pipeline processes it, **Then** output time series with naively extracted amplitude/phase, unwrapped phase, and sanitized phase.
2. **Given** noisy packets containing spikes (              amplitude/phase), **When** Hampel filter + Savitzky-Golay smoothing is applied, **Then** the output has <5% of points flagged as outliers and no visible discontinuities in measured stats.

---

### User Story 2 - Dimensionality reduction and signal selection (Priority: P2)

Researcher needs PCA components and subcarrier ranking to select a stable subset for model input.

**Why this priority**: Lower-dimensional signals reduce overfitting and improve model generalization; this is the core “stability” objective.

**Independent Test**: Compute PCA on cleaned data and evaluate explained variance.

**Acceptance Scenarios**:
1. **Given** filtered, normalized feature matrix (packet x subcarrier), **When** PCA runs for top 5 components, **Then** cumulative explained variance >= 80% and selected PCs are saved for subsequent analysis.

---

### User Story 3 - Stable dataset export plus quality metrics (Priority: P3)

Researcher needs an artifact containing standardized training data (spectrogram tensors + labels) and a summary quality report.

**Why this priority**: Guarantees the end goal: a robust dataset, not just intermediate variables.

**Independent Test**: Export dataset to disk and verify metadata includes SNR, entropy, and outlier rates.

**Acceptance Scenarios**:
1. **Given** PCA-reduced signals, **When** spectrogram/cnn-tensor generation is executed, **Then** output dataset files are created with accompanying `dataset_quality.json`.

---

### Edge Cases

- Input file has variable subcarrier counts across packets (partial packet losses).
- All packets are nearly static (little or no motion), requiring no movement handling path.
- Data contains malformed packet entries (error in JSON parse, NaNs, infinities).
- Very short captures (<100 packets); ensure pipeline does not crash and issues a warning.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse raw CSI data into complex subcarriers and compute amplitude+phase for each packet.
- **FR-002**: System MUST apply phase unwrapping and robust linear phase sanitization to remove SFO/CFO trends.
- **FR-003**: System MUST detect and suppress outliers using Hampel filtering on amplitude and phase with configurable window and threshold.
- **FR-004**: System MUST apply smoothing (e.g., Savitzky-Golay) after outlier filtering and retain config for reproducibility.
- **FR-005**: System MUST apply frequency-domain bandpass filtering (e.g., elliptic 0.1–0.6 Hz) on both amplitude and phase signals.
- **FR-006**: System MUST perform dimensionality reduction (e.g., PCA on cleaned signal matrix) and expose explained variance.
- **FR-007**: System MUST select stable subcarriers/components based on signal quality metrics (SNR, spectral entropy, variance energy) and keep top-N for dataset.
- **FR-008**: System MUST export final dataset (tensor arrays, metadata) with explicit quality metrics and a reproducibility log.

### Key Entities *(include if feature involves data)*

- **CSIPacket**: raw input row, includes timestamp, RSSI, payload bytes/JSON list, device metadata.
- **PreprocessedSeries**: decomposed amplitude, unwrapped phase, sanitized phase arrays for each packet.
- **NoiseFilterConfig**: parameters for Hampel, Savitzky-Golay, bandpass, etc.
- **DimReductionModel**: PCA object with components, explained variance and subcarrier loadings.
- **DatasetArtifact**: output package with `features`, `labels`, and `quality` metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Post-filter SNR is improved by at least 6 dB on average compared to raw data for at least 80% of validation files.
- **SC-002**: PCA top-5 components explain >=80% variance in preprocessed data in 95% of validation sessions.
- **SC-003**: Generated dataset includes `dataset_quality.json` with completion metrics, and no critical step fails in 100% of runs.
- **SC-004**: Pipeline handles a dataset with 100k packets and completes within 15 minutes on a modern research workstation (16 CPU cores, 32 GB RAM) without OOM.

## Assumptions

- Input data follows CSI format used in current notebook (`data` column is JSON list or array of [imag, real,...]).
- Phase unwrapping + sanitization are stable for small sample rates (>=25 Hz) and known breathing range (0.1-0.6 Hz).
- Dataset export requirements are research-optimized (not production ML service); format can be NumPy `.npz` + JSON.
- No online ingestion requirement; batch processing is acceptable.
- Existing `csi_processing.ipynb` code patterns are baseline and should be refactored into reusable modules (`csi_processing.py`).

