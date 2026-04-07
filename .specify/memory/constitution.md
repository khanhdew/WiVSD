<!--
Sync Impact Report:
- Version change: N/A -> 0.1.0
- Modified principles: Added all 5 foundational principles focused on research-quality correctness.
- Added sections: Section 2 (Research & Data Quality Standards), Section 3 (Development Workflow & Quality Gates).
- Removed sections: placeholder tokens removed.
- Templates requiring updates: ✅ .specify/templates/plan-template.md (Constitution Check aligns with governance); ✅ .specify/templates/spec-template.md (QA scopes consistent); ✅ .specify/templates/tasks-template.md (task group guidance aligned); ⚠ .specify/templates/commands/* (not present, none required).
- Follow-up TODOs: none.
-->

# WiVSD Research Constitution

## Core Principles

### I. Research-Centered Correctness
The project MUST be driven by empirical traceability: every architecture choice, signal processing step, and model decision is supported with clear experimental evidence (data, benchmarks, citations). Proof-of-concept outputs are valid only if repeatable under documented conditions. The priority is correctness over optimization when the research context is unclear.

### II. Data Quality & Reproducibility
Raw CSI acquisition, preprocessing, and derived features MUST be versioned and stored with metadata (device config, timestamp, preprocessing parameters). Pipelines MUST include deterministic transforms and seed controls. Non-deterministic or approximate algorithms are allowed only when performance needs are justified by experiments.

### III. Test-First Validation (NON-NEGOTIABLE)
All code MUST have automated tests before feature merge (unit + regression at minimum). For research code, include dataset-orientation tests with a narrow validation set that reproduces key published behavior. Changes that reduce accuracy by >5% against baseline MUST be gated by review and revert plan.

### IV. Peer Review & Statistical Rigor
Code and analysis MUST be reviewed by at least one domain peer before integration. Experiments MUST report metrics with confidence intervals or repeat-run statistics where possible. Claims require reproducible artifact or script accompanying PR.

### V. Simplicity, Observability, Traceable Metric Reporting
Design MUST favor readable, testable code paths. Logging/plot outputs MUST include units and interpretation comments. Each model or signal extraction stage MUST expose measurable quality metrics (e.g., SNR, spectral entropy, detection reliability) for validation and drift monitoring.

## Research & Data Quality Standards

- Data collection and preprocessing standards MUST be documented in `README.md` and research notes.
- CSI handling MUST distinguish between guard and signal subcarriers; transients and artifacts MUST be annotated.
- Scientific assumptions MUST be explicit in docs (e.g., breathing band 0.1–0.6 Hz, sampling frequency 100 Hz).
- New datasets or config changes require a regeneration path and regression comparison to baseline.

## Development Workflow & Quality Gates

- Start with `speckit.plan` for scoping, include a ‘Constitution Check’ block referencing this constitution.
- All PRs MUST include a checklist: [x] run tests; [x] reproduce key research notebook output; [x] update regression result logs.
- Merge is blocked until all principle checkpoints are signed and a collaborator has validated no principle regression.
- Fast-fail for any changes that break the baseline dataset reproduction script.

## Governance

- Constitution is authoritative for development conduct and MUST be reviewed every quarter.
- Amendments require a PR with new text, rationale, and take effect only after one reviewer (not the author) approves.
- Non-substantive wording/typo updates are PATCH; new principles or resource changes are MINOR; principle removals are MAJOR.
- Compliance monitoring: include a pointer in `README.md` and the branch-level `CONSTITUTION_CHECK.md` when possible.

**Version**: 0.1.0 | **Ratified**: 2026-03-29 | **Last Amended**: 2026-03-29
<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->
