# Tasks: CSI signal processing + stable dataset pipeline

**Input**: Design documents from `/specs/001-signal-processing-dataset/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Initialize Python project structure in `src/csi_preprocessing` and `tests` from implementation plan
- [x] T002 Configure dependencies in `pyproject.toml` (numpy, pandas, scipy, scikit-learn, hampel, plotly)
- [ ] T003 [P] Add code style and lint config: `ruff.toml`, `pre-commit` hooks, `black` default
- [ ] T004 [P] Add CI job skeleton in `.github/workflows/ci.yml` to run `pytest`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T005 Implement core CSI parsing module in `src/csi_preprocessing/parse.py` (CSIPacket and `compute_amplitude_phase`)
- [x] T006 [P] Implement phase processing module in `src/csi_preprocessing/filters.py` (unwrap + sanitize + Hampel + SG + elliptic bandpass)
- [x] T007 Implement PCA and feature reduction module in `src/csi_preprocessing/pca.py` (top 5 PCs, explained variance)
- [x] T008 Implement dataset assembly/export module in `src/csi_preprocessing/dataset.py` (STFT, CNN tensor preparation, NPZ/JSON output)
- [x] T009 Implement CLI entrypoint in `src/csi_preprocessing/cli.py` (input/output, config, logging, metric generation)
- [x] T010 Add baseline unit tests in `tests/unit/test_parse.py` for amplitude/phase extraction
- [x] T011 Add baseline unit tests in `tests/unit/test_filters.py` for phase/smoothing and bandpass
- [x] T012 Add baseline unit tests in `tests/unit/test_pca.py` for PCA variance checks and selection
- [x] T013 Add baseline unit tests in `tests/unit/test_dataset.py` for artifact output format and metadata

---

## Phase 3: User Story 1 - Clean and normalize CSI stream (Priority: P1)

**Goal**: Build robust preprocessing path for raw CSI to cleaned per-subcarrier streams

**Independent Test**: `tests/integration/test_preprocessing_pipeline.py` accepts raw sample and verifies outlier and smoothing metrics

- [x] T014 [P] Add integration test for complete preprocessing path (raw -> amp/phase -> behavior checks)
- [x] T015 [US1] Implement TSV/CSV loader in `src/csi_preprocessing/parse.py` with malformed record handling
- [x] T016 [US1] Implement `unwrap_phase` and `sanitize_phase_robust` in `src/csi_preprocessing/filters.py`
- [x] T017 [US1] Implement `apply_hampel` and `apply_savgol` in `src/csi_preprocessing/filters.py`
- [x] T018 [US1] Implement `elliptic_bandpass` in `src/csi_preprocessing/filters.py`
- [x] T019 [US1] Add result metrics in `src/csi_preprocessing/dataset.py` (outlier_rate, snr)

---

## Phase 4: User Story 2 - Dimensionality reduction and signal selection (Priority: P2)

**Goal**: Convert cleaned data into stable PCA features with explained variance

**Independent Test**: `tests/integration/test_pca_workflow.py` checks top-5 explain >=80%

- [x] T020 [P] Implement PCA training function in `src/csi_preprocessing/pca.py` (amp + phase separate)
- [x] T021 [US2] Implement component ranking and selection based on stable metrics
- [x] T022 [US2] Integrate selected PCA components into dataset pipeline in `src/csi_preprocessing/dataset.py`
- [x] T023 [US2] Add integration test for PCA+selection to pipeline

---

## Phase 5: User Story 3 - Stable dataset export plus quality metrics (Priority: P3)

**Goal**: Produce NPZ dataset with JSON quality metadata usable for training and inference

**Independent Test**: `tests/integration/test_dataset_export.py` asserts output keys and JSON fields

- [x] T024 [P] Implement `build_cnn_input` in `src/csi_preprocessing/dataset.py` (STFT + scaling)
- [x] T025 [US3] Implement final dataset export function in `src/csi_preprocessing/dataset.py` (npz + json)
- [x] T026 [US3] Add dataset quality report generator (snr, spectral entropy, outlier rate)
- [x] T027 [US3] Add integration test for full export and minimal loading

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: cleaning, docs, extra tests after core stories

- [ ] T028 [P] Add `docs/` usage guide for this pipeline and link from README
- [ ] T029 [P] Add performance benchmark script in `scripts/benchmark.py`
- [ ] T030 [P] Add additional edge-case tests in `tests/integration/test_downsampled_data.py`
- [ ] T031 [P] Update `quickstart.md` and `README.md` with final command examples
- [ ] T032 [P] Run full regression (existing notebook reproduction) and record results in `research.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- Setup (Phase 1) must complete before Foundational (Phase 2)
- Foundational (Phase 2) must complete before all user stories
- User stories can be worked in parallel once foundational done
- Polish phase depends on all user stories

### User Story Dependencies
- US1: core path, no dependency other stories
- US2: depends on US1 output
- US3: depends on US2 output

### Parallel Example
- T003, T006, T007, T008 can run in parallel after T005
- US1/US2/US3 implementation can run in parallel once Phase 2 is complete

## Implementation Strategy

### MVP first
1. Setup
2. Foundational modules + tests
3. Deliver US1 with test coverage
4. Then US2 and US3 incrementally

### Incremental Delivery
1. Release preprocessing library only (MS1)
2. Add PCA components (MS2)
3. Add final dataset export (MS3)

