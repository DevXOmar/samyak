# Phase 1 handoff

Implemented the local Python pipeline across all eight PS modules, including a train-only Precedent Engine, exact-case oracle confirmation, context-aware candidates and regression rejection. The original problem statements are preserved.

## Commands

`make setup && make runner && make train`, then `make dev` (http://127.0.0.1:3000; API docs on :8000/docs). With the stack running, `make demo`. Validation: `make check`. Full source/witness rebuild: `make reproduce`. Requires Python 3.11+, Node 22.12+ and Linux Docker. See README for endpoint/replay details and `.env.example` for optional LLM configuration. No LLM key is needed.

## Measured results — 13 November 2026

- Final checks: **29 backend tests and 5 frontend tests**; Ruff lint/format, ESLint, TypeScript and Next production build pass. Docker integration ran, rather than skipping. Python tests emit third-party deprecation/collection warnings.
- 21 licensed seed entries / 19 distinct algorithm problems; 127 mutants generated, **92 witnessed**, 35 unkilled/unresolved excluded. Combined corpus: **111 pairs**; deduplicated rows: 125 train / 4 validation / 10 calibration / 12 test. Three absent seed paths and HTTPie bug 1/2 404s are recorded verbatim in `data/source_manifest.json`.
- RF and XGBoost binary/family heads were trained independently. XGBoost risk uses sigmoid calibration on a separate 10-row cohort; this small cohort cannot establish strong calibration reliability. Two consecutive `make train` runs reproduced identical model artifact bytes after removing process-specific sklearn cache data and normalizing tree padding.

| Untouched cohort | Rows | XGB PR-AUC | XGB ROC-AUC | XGB F1 |
|---|---:|---:|---:|---:|
| REAL_BUGSINPY | 6 | 0.500 | 0.444 | 0.571 |
| SYNTHETIC_ALGORITHM | 6 | 1.000 | 1.000 | 0.909 |

These are tiny, imbalanced cohorts, not a broad accuracy claim. RF results, family confusion matrices/abstention and all actual scores are in `data/models/metrics.json`. **ML-off/on localization has no measured uplift**: real Top-1/Top-3 = 2/3; algorithm Top-1/Top-3 = 0/5 for every arm. No test-based parameter tuning was performed; hyperparameters were fixed.

| Source demo | Actual verdict | One observed job duration |
|---|---|---:|
| binary_search | `VALIDATED_ON_TESTS` | 8.695 s |
| average | `INCONCLUSIVE_NO_OUTPUT_ORACLE` | 3.424 s |
| caller_regression | `VALIDATED_ON_TESTS` | 15.811 s |

The caller fixture includes an automatically rejected sentinel-changing candidate. Average's exact empty→0 confirmation creates a new A-oracle revision that validates; accepting only the empty input domain receives runtime-fault-only validation in the integration test. These durations are individual jobs, not aggregate latency estimates. Runtime comparisons remain `PERFORMANCE_INCONCLUSIVE`; measured median/p95 samples and patch footprints are retained.

A fresh non-fixture `position_of(values, needle)` submission through Next's API proxy completed with **VALIDATED_ON_TESTS** on 15 cases, including a rejected candidate. Export hashes verified and original plus both candidates replayed with **MATCH** against the recorded runner. Source fixtures contain code, not cached results. Browser observation verified a completed boundary analysis, live progress, predictions, line ranking and the repair tournament. The browser access host/native window later became unavailable; no final browser confirmation-flow or narrow-screen screenshot is claimed. That confirmation flow was exercised through real API jobs and integration tests.

Current model ID: `463675ab8bdff1a9a345f0df5b853f4495ef1e8945e31df752278b556009da4e`. Artifact SHA-256: `c6931ef9eec3d844336325b8aa73b8861a30eb6792fa00830622215c9d32d987`. Immutable revisions are retained under `data/models/versions/`; CURRENT selects the serving revision. Fresh replay job: `b2d3d75528c94984afc1078ae6fb1e62`; runner `sha256:3f131ccf1fd39aa3f80c2c6f1ff8a9c3ec834e29c5e7b694d41a210902ae480d`. Local demo ZIPs/results are in ignored `var/`.

## Boundaries and remaining work

Docker-only isolation is **development-grade**, never a production hostile multi-tenant sandbox. Execution fails closed if Docker/image is missing. No submitted or historical program is executed in API/training interpreters. Supported execution is bounded pure Python functions with at most four positional parameters for inference, finite JSON inputs/results and a fixed standard-library allowlist. Class methods, dynamic dispatch, exception CFG edges, aliasing and cross-module packages are incomplete. All available authored/caller tests are rerun rather than relying on a complete graph.

The guard-removal family has only two distinct training examples and is deliberately omitted from the learned family head. The supported index family has four. Rules and deterministic guard candidates still function. There is no broad family-held-out study, external QuixBugs assessment, calibrated novelty classifier, retrieval repair-success ablation or claimed ML localization benefit. QuixBugs has zero training/retrieval/prompt/tuning exposure. The optional LLM adapter is implemented and disabled by default; no external paid endpoint was exercised.

B properties currently require an explicit sorting contract. Generated domains remain guesses until accepted; domain confirmation is exact-input scoped, output confirmation exact-input/output scoped. Shrinking preserves an observed exception and does not transfer an oracle/domain to a different tuple. Candidate budgets are six deterministic plus up to two LLM edits. Seven-call runtime samples do not justify speedup claims. A successful patch is validated only on its recorded authoritative cases; unresolved semantics remain visible.

## Phase 2 extension boundary — not implemented

1. Expand/audit project-disjoint real source pairs and independently checked algorithm parents; obtain sufficient guard/family support, untouched family/external cohorts and confidence intervals. Measure whether ML and retrieval improve localization/repair before promoting their contribution.
2. Extend scope-aware CFG/def-use, dependency contracts, affected-caller input synthesis and additional independently justified B properties; improve domain inference and shrinking coverage while keeping exact confirmation semantics.
3. Broaden safe CST repair families and evaluate the configured LLM adapter against hidden tests; add controlled paired runtime sampling and normalized AST edit/blast-radius measurements.
4. Before any hostile/public execution, move to an independently hardened runner boundary (gVisor/microVM), add tenant/auth/retention/resource policy and adversarial assessment. Keep SQLite/local workflow until measured requirements justify changing it.
5. Only after these gates, implement and measure the blueprint's deeper novelty, metamorphic, semantic-twin and risk-budget innovations. Additional languages and speculative infrastructure are deferred.
