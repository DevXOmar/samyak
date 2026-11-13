# Phase 2 handoff — 13 November 2026

SAMYAK now has five connected, light/dark investigation workspaces and ten bounded, operational USPs. The existing backend, source datasets, independently trained artifacts, Docker harness, SQLite worker and Phase 1 endpoints are preserved. New contracts are additive v1.1, with regenerated OpenAPI TypeScript types. No new service or queue infrastructure was introduced.

## Start and reproduce

```sh
make setup
make runner
make dev                   # http://127.0.0.1:3000; API docs :8000/docs
make demo-phase2           # with dev running: 12 real jobs + evidence ZIPs
make check                 # lint, typecheck, backend/frontend tests, production build
cd frontend && npx playwright install chromium && npm run test:e2e
```

The shipped model is ready to load; `make train` remains available and unchanged. `make e2e` also runs Playwright, starting the existing dev stack when absent. Temporary jobs, evidence bundles, traces, reports and screenshots are not committed.

## Delivered and verified

- Warm matte palette, local Geist/Geist Mono, custom Monaco themes, minimap/search/folding, exact Unicode source spans, diagnostic hovers/heat gutters, fullscreen/Escape, vertical resizing, keyboard analysis, file/test tabs and source/test evidence invalidation.
- React Flow AST/call/CFG/def-use views with synchronized source inspection and explicit unresolved edges. No graph dump is substituted for interactive inspection.
- Counterexample/Contract Studio with no-hint inference, actual failures, bounded delta/Hypothesis minimization, repeated replay, exact Yes/No/Edit/domain confirmations and immutable reruns. Existing A expectations can be retracted; later exact confirmation can restore authority without widening the input contract.
- Repair Arena with forced desktop side-by-side DiffEditor, readable test inputs, candidate gates/ranks, historical priors and real retrieval-on/off execution. Caller regressions, risk-policy reasons and measured patch footprints are inspectable.
- Model Lab & Vault with actual RF/XGB metrics, cohort data, family confusion matrices, unchanged ML-off/on ablation, heuristic novelty, deterministic licensed evidence archives and exact-image verification/replay.
- Contract-justified sorting Shield and AST-identical semantic twins execute real source variants. Every unsupported eligibility path states `NOT_SUPPORTED` with a reason.

## Actual verification

- **48 backend tests**, including real Docker containment, all Phase 1 regressions and the new witness/retrieval/ledger/twin/Shield/contract policy checks.
- **5 frontend unit tests**; ESLint, TypeScript, Ruff lint/format and optimized Next.js production build pass.
- **8 full Playwright workflows pass**: editing→analysis→finding→graph→repair→stale evidence; oracle/domain/No revisions; caller rejection; unfamiliar-code abstention; 390/1440/1920px themes/fullscreen; SSE transport-abort recovery; witness/retrieval/twin/ledger actions; declared-property Shield. The editor/theme tests were also rerun after final diff/contrast refinements.
- `make demo-phase2` completed **12 actual queued jobs**, preserving successful repair, rejected caller fix, unknown-contract abstention, exact A confirmation and verified experiment outputs. ZIPs and result manifests are in ignored `var/`.
- Actual light/dark, mobile, analyzed workbench, repair and model layouts were captured/inspected with Playwright. Browser inspection found and corrected DiffEditor disposal, selection/cursor interference, theme persistence/transition contrast and automatic inline-diff fallback.
- Production npm audit: **zero reported vulnerabilities** at verification time. Backend tests retain three non-failing third-party/collection warnings.
- A baseline diff confirmed no changes to `data/`, the container `runner/` harness, requirements, numeric structural features or training scripts. The host adapter gained canonical Docker image-name handling for Docker Desktop compatibility.

## Evidence and limits

See `USP_EVIDENCE.md` for each mechanism, route, UI action, artifact and acceptance test; `TRACEABILITY.md` maps the complete 100-mark PS rubric; `JUDGE_DEMO.md` provides the seven-minute live flow and truthful fallbacks.

The original model ID remains `463675ab8bdff1a9a345f0df5b853f4495ef1e8945e31df752278b556009da4e`. Train/validation/calibration/test rows remain **125/4/10/12**. There is **no measured ML localization uplift**, no external QuixBugs/family-holdout evaluation and insufficient guard-family training support. Novelty thresholds are explicitly heuristic. The optional external LLM adapter was not exercised; local deterministic repairs require no key.

Docker-only isolation remains development-grade and local-only. Static dependency/CFG analysis is bounded and incomplete; full available suites run. Sorting properties support a single finite integer list; twins support conservative AST-identical parenthesization, refusing uncertain equivalence. Counterexample reduction preserves an observed signature within a finite probe budget, not a global minimum or a transferred oracle. Runtime samples remain `PERFORMANCE_INCONCLUSIVE`; no speedup is claimed. Hashes provide integrity, not authentication or formal correctness.

Progress was committed and pushed incrementally on the original `main` branch to `origin/main`; no history rewrite or force push was used. Development services can be restarted with `make dev` after verification teardown.
