# PS requirements and complete 100-mark traceability

The mandatory PS/rubric comes from `ProblemStatement/Hackthon.docx`; v2 architecture and USP scope come from `Samyak_Technical_Blueprint.md`. This matrix describes delivered mechanisms and tested bounds, not an award or a claimed score.

| Rubric criterion | Available marks | Implementation and reviewable evidence |
|---|---:|---|
| Dataset engineering and preprocessing | 10 | Pinned/licensed source-only BugsInPy extraction and TheAlgorithms mutation corpus; lineage splits before mutation/TF-IDF; dedup; actual sandbox witnesses; source/corpus manifests and leakage tests. 111 pairs, documented acquisition failures and unsupported guard-family volume. |
| Code representation and feature extraction | 15 | AST/tokens/symtable/LibCST spans, numeric features, bounded CFG/lexical def-use/call graphs, explicit unresolved calls; real interactive React Flow AST/call/CFG/def-use and synchronized Monaco source. Parser and AST artifact tests. |
| ML model development and defect prediction | 20 | Existing independent RF/XGBoost binary and family heads, TF-IDF+AST, grouped untouched cohorts, actual calibration/confusion matrices/model IDs; Model Lab and heuristic novelty/disagreement. Tiny cohorts and poor cross-project behavior remain explicit. |
| Semantic bug localization | 15 | Exposed risk/family/rule/graph/Ochiai contributions, exact suspicious spans, coverage, graph/source navigation and frozen ML-off/on ablation. **No measured ML uplift** is claimed. |
| Automated repair and optimization | 15 | LibCST/context-aware templates, train-only precedent-ranked operators, optional LLM adapter, real retrieval-on/off execution, DiffEditor and lexicographic candidate tournament. AST/line footprint and caller impact are measured; runtime is honestly inconclusive where noisy. |
| Test generation and regression validation | 15 | Explicit Hypothesis inference, reproducible/minimized witnesses, A/B/I/C domains, exact confirmation/rejection/property revisions, actual restricted Docker runs, full caller suite, justified metamorphic checks, distinct timeout/flake/error/unresolved states, exact-image replay and tamper checks. |
| Innovation and technical demonstration | 10 | Ten bounded, wired USPs with concrete mechanisms/actions/artifacts/tests in `USP_EVIDENCE.md`; four live source demonstrations, evidence vault, semantic twins, risk budget and Playwright workflows. No cached results masquerade as execution. |
| **Total rubric coverage** | **100** | **Coverage of the rubric is not a self-assigned score or proof of generalization.** |

| Mandatory module / advanced requirement | Implementation | Acceptance evidence |
|---|---|---|
| M1 Code Intelligence | `structure.py`, `scripts.py`, `atlas.py`, Fault Atlas and Monaco | Non-executing parser, exact source/annotation separation, inspectable AST, CFG/def-use/unresolved calls; parser/atlas/browser tests |
| M2 Defect Prediction | Existing `data/`, `scripts/train.py`, `ml.py` | Real independently trained artifacts, preserved model IDs/cards, frozen cohort metrics and train-only novelty references; leakage/model tests |
| M3 Semantic Localization | `structure.localize`, evidence rail, heat gutter | Each signal exposed; click L3 in live binary search; actual ML-on/off Top-1/Top-3/MRR table |
| M4 Logical Analysis | Existing rule detectors + Ruff/Bandit | Bounds, condition, division, empty, None, mixed-return and unsafe-call hypotheses; observed/confirmed evidence and impact-based severity remain separate from ML |
| M5 Repair | `repair.py`, `precedent_experiment.py`, `impact.py`, Repair Arena | Real applicable candidates, context/precedents, gate failures and verified survivors on the same suite; user candidates use the same validation endpoint |
| M6 Test Generation | `inference.py`, `investigations.py`, `metamorphic.py`, Contract Studio | Untyped inference, exact expectations/domain actions, semantic/runtime witnesses, replay, Hypothesis shrink scope, B transformations and rejection ledger |
| M7 Validation | Preserved `runner/` (function and SCRIPT paths), `runner.py`, deterministic `ledger.py` | Docker containment, fail-closed unavailable state, actual original/patch tests, caller-regression rejection, runtime-only versus semantic verdicts, replay and tamper tests |
| M8 Dashboard | Existing Next/shadcn/Monaco refactored into connected workspaces | Light/dark responsive browser tests, actual SSE/timeline, real model/graph/witness/repair/export data, stale-evidence invalidation and unavailable states |
| Advanced: unseen prediction | Group-disjoint cohorts + heuristic novelty/disagreement/AST novelty | Correct-but-suspicious fixture remains inconclusive; no hidden cohort, calibration or generalization improvement is invented |
| Advanced: context-aware repair | Call/def-use context + bounded reverse impact + full caller tests | Tempting `None→-1` repair is rejected for downstream `contains` regressions; boundary alternative survives |
| Advanced: regression prevention | Identical frozen available suites, explicit gates and replay | Passing authored/caller checks preserved; errors/timeouts/flakes remain distinct; tests and Playwright inspect actual rejection reasons |

See `USP_EVIDENCE.md` for every USP's route, action, test, artifact and unsupported paths; see `JUDGE_DEMO.md` for the live walkthrough. The original Phase 1 handoff remains an immutable historical record.

## Script submissions (additive v1.2)

- M1/M3/M4: module AST/tokens/source spans, bounded CFG, lexical def-use, resolved/unresolved calls and applicable logical/security hypotheses. Actual traceback lines are tagged `OBSERVED_RUNTIME_FAULT`, with domain unconfirmed; definitions/imports are not labeled observed executable statements.
- M2: function feature vectors, RF/XGBoost artifacts, cohorts and metrics remain unchanged. Script-only ML output is `NOT_APPLICABLE`; no synthetic function or learned module score is invented.
- M7: SCRIPT jobs execute as `__main__` only in the existing Docker boundary, with bounded stdin and actual streams/exit/coverage/duration/exception/timeout evidence. `EXECUTED_SUCCESSFULLY` is distinct from validation. Scripts without output oracles cannot certify patches.
- M8: distinct Run/Analyze actions and shortcuts, read-only xterm Output, clickable Problems/Trace, panel resize, stdin and source/test evidence invalidation. Monaco/DiffEditor, themes, function fixtures and all ten existing USP flows are retained.
- Acceptance: `backend/tests/test_scripts.py` exercises production API/worker/SSE, Docker scripts, stdin/main/loops/crashes/timeouts, fail-closed safety, actual containment, immutable reruns, bundle evidence and unchanged model metadata. `frontend/e2e/scripts.spec.ts` covers real UI→API→Docker→output, exact navigation, clear/dismiss, stale output, keyboard, resizing/themes/mobile/fullscreen and C-language guidance. Existing Phase 2 acceptance and demo gates remain required.
- Bounds: static CFG/def-use remain approximations. SCRIPT execution is one bounded observation, without inferred broad stdin contracts, script-specific repair certification, interactive shells, live stdout streaming or cancellation. Existing function oracles/repair semantics are unchanged.
