# Phase 1 requirement traceability

| Requirement | Implementation | Acceptance evidence |
|---|---|---|
| M1 Code Intelligence | `backend/samyak/structure.py` | Parser non-execution, exact spans, runtime/annotation separation, CFG and unresolved-call tests |
| M2 Defect Prediction | `scripts/data_sources.py`, `build_corpus.py`, `train.py`, `backend/samyak/ml.py` | Actual pinned sources, witnessed mutants, RF/XGB risk/family artifacts, grouped metrics/confusion matrices and leakage tests |
| M3 Semantic Localization | `structure.localize` | Exposed ML/rule/graph/Ochiai signals; frozen ML-on/off ablation in model metrics; live binary-search line ranking |
| M4 Logical Analysis | `structure.analyze`, Ruff/Bandit scanners | Bounds, off-by-one, divisor, empty, optional/None, mixed returns, unsafe calls/deserialization; hypotheses remain qualified; severity independent of probability |
| M5 Repair | `backend/samyak/repair.py` | Immutable LibCST candidates, normalized historical operator priors, context, syntax/signature/security/edit gates, configurable LLM endpoint |
| M6 Test Generation | `inference.py`, `contracts.py`, contract endpoints | Explicit Hypothesis strategies, untyped average inputs, reproducible error observations, bounded shrinking, exact A/I confirmation reruns and declared B sorting property |
| M7 Validation | `runner/`, `runner.py`, `repair.validate` | Actual non-root/read-only/network-off containment tests; original/patch matrices; rejected harmful patch; domain-unconfirmed abstention; separate runtime-only verdict; replay |
| M8 Dashboard | `frontend/src/app/page.tsx`, Monaco, shadcn/ui components | Browser-observed complete pipeline, line markers, learned risk, all 8 output states, diffs, generated tests, confirmation controls and ZIP export |
| Advanced: unseen prediction | Group-disjoint training/evaluation, unfamiliarity abstention | Real project and algorithm problem holdouts; small cohorts, no measured broad generalization and no external QuixBugs assessment claimed |
| Advanced: context repair | Call/def-use graph, complete function context, caller test suite | Sentinel-changing local patch breaks `contains`; regression gate rejects it while a boundary patch validates |
| Advanced: regression prevention | Same frozen tests for every candidate, full available suite, repeatability | Previously passing authored caller tests retained, regression/timeout/flake/error/unresolved checks distinct |

Only the Phase 1 subset is implemented. The blueprint's ten larger innovations are not all claimed as delivered. Historical similarity is advisory; one exact confirmation is not a universal contract; test validation is not a proof.
