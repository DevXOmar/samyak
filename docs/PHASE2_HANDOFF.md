# Phase 2 handoff — 13 November 2026

SAMYAK now has five connected, light/dark investigation workspaces and ten bounded, operational USPs. The existing backend, source datasets, independently trained artifacts, Docker harness, SQLite worker and Phase 1 endpoints are preserved. Initial Phase 2 contracts were additive v1.1 (the script addendum below adds v1.2), with regenerated OpenAPI TypeScript types. No new service or queue infrastructure was introduced.

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

## Initial Phase 2 verification

- **48 backend tests**, including real Docker containment, all Phase 1 regressions and the new witness/retrieval/ledger/twin/Shield/contract policy checks.
- **5 frontend unit tests**; ESLint, TypeScript, Ruff lint/format and optimized Next.js production build pass.
- **8 full Playwright workflows pass**: editing→analysis→finding→graph→repair→stale evidence; oracle/domain/No revisions; caller rejection; unfamiliar-code abstention; 390/1440/1920px themes/fullscreen; SSE transport-abort recovery; witness/retrieval/twin/ledger actions; declared-property Shield. The editor/theme tests were also rerun after final diff/contrast refinements.
- `make demo-phase2` completed **12 actual queued jobs**, preserving successful repair, rejected caller fix, unknown-contract abstention, exact A confirmation and verified experiment outputs. ZIPs and result manifests are in ignored `var/`.
- Actual light/dark, mobile, analyzed workbench, repair and model layouts were captured/inspected with Playwright. Browser inspection found and corrected DiffEditor disposal, selection/cursor interference, theme persistence/transition contrast and automatic inline-diff fallback.
- Production npm audit: **zero reported vulnerabilities** at verification time. Backend tests retain three non-failing third-party/collection warnings.
- At the initial Phase 2 handoff, a baseline diff confirmed no changes to `data/`, the container `runner/` harness, requirements, numeric structural features or training scripts. The host adapter gained canonical Docker image-name handling for Docker Desktop compatibility.

## Evidence and limits

See `USP_EVIDENCE.md` for each mechanism, route, UI action, artifact and acceptance test; `TRACEABILITY.md` maps the complete 100-mark PS rubric; `JUDGE_DEMO.md` provides the seven-minute live flow and truthful fallbacks.

The original model ID remains `463675ab8bdff1a9a345f0df5b853f4495ef1e8945e31df752278b556009da4e`. Train/validation/calibration/test rows remain **125/4/10/12**. There is **no measured ML localization uplift**, no external QuixBugs/family-holdout evaluation and insufficient guard-family training support. Novelty thresholds are explicitly heuristic. The optional external LLM adapter was not exercised; local deterministic repairs require no key.

Docker-only isolation remains development-grade and local-only. Static dependency/CFG analysis is bounded and incomplete; full available suites run. Sorting properties support a single finite integer list; twins support conservative AST-identical parenthesization, refusing uncertain equivalence. Counterexample reduction preserves an observed signature within a finite probe budget, not a global minimum or a transferred oracle. Runtime samples remain `PERFORMANCE_INCONCLUSIVE`; no speedup is claimed. Hashes provide integrity, not authentication or formal correctness.

Progress was committed and pushed incrementally on the original `main` branch to `origin/main`; no history rewrite or force push was used. Development services can be restarted with `make dev` after verification teardown.

## Script execution addendum — 13 November 2026

Ordinary Python modules are now first-class submissions. Additive **v1.2** contracts introduce `AnalysisRequest.mode` (`ANALYZE` default / `SCRIPT`) and bounded `stdin`, plus a separate `Report.script_result`. Rebuild with `make runner`, then `make dev`; the committed model works without retraining. Existing jobs remain immutable. Historical execution availability stays separate from live capability checks.

- **Run** (⌘/Ctrl+Enter) executes the complete source as `__main__`; **Analyze source** (⌘/Ctrl+Shift+Enter) retains the eligible function investigation pipeline. Script-only Analyze runs even with no tests. Optional stdin supports `input()` inside the container only.
- `scripts.py` adds module statement spans, bounded control flow, lexical def-use, calls and applicable rule hypotheses. Actual traceback frames localize observed faults without confirming their domains. Imports/definitions remain structural facts and are excluded from observed executable-line coverage. Existing function numeric features and model training are unchanged.
- `runner/script_case.py` captures real stdout/stderr, exit code, traceback/source lines, executable-line coverage and one-shot duration, with CPU/wall/output bounds. The Docker adapter retains all network, non-root, read-only-root, PID/RAM/capability/no-secrets restrictions. Missing runner remains `EXECUTION_UNAVAILABLE`; security-denied submissions remain denied. Function execution is preserved.
- A script success is **`EXECUTED_SUCCESSFULLY`**, never repair validation or proof of correctness. Script-only ML is **`NOT_APPLICABLE`**, with the explicit UI explanation. No script repairs or guessed output oracles are generated. For mixed function/script Analyze, the separate module observation does not certify candidate script behavior; existing validation verdicts remain limited to the frozen function suites.
- Monaco retains themes, tabs, graphs and DiffEditor. It now has Run/Analyze actions, a bounded stdin editor, editor status, and a height-adjustable **Output / Problems / Execution Trace** panel using pinned xterm/fit packages as a read-only viewer. Trace/problem locations select exact source spans. Clear affects only the view; export/replay retains evidence. Source/stdin/test edits invalidate old output. Script recommendations are dismissible per submission.
- Python language diagnostics explain C `printf` without compiling or translating it. Unsafe imports/names remain unsupported. Bounded `input()` is the only script-specific application-allowlist exception.

Verification for this addendum: **`make check` passes (67 backend tests, 7 frontend tests, Ruff/ESLint/typecheck and production build)**. New backend tests use actual Docker for hello/loops/main guards/stdin/NameError/zero division/timeouts, stderr/exit status, containment, immutable reruns, model-metadata preservation and mixed-script localization. **All 18 Playwright workflows pass**, including the original eight Phase 2 workflows and the new script/readiness acceptance cases. Browser acceptance covers script output and trace navigation, clear/dismiss, Run shortcut, source/stdin invalidation, resizing/fullscreen and light/dark/mobile layouts. The existing **12-job `make demo-phase2` circuit passes**, preserving all ten USP mechanisms. A freshly exported stdin script bundle was replayed against its exact image. `data/`, training scripts, dependency lock for Python and frozen ML metrics are unchanged; no retraining was performed.

Bounds: stdout arrives at bounded job completion, not as a live terminal stream. Job cancellation and interactive shells are unsupported. Forced resource termination may lack complete coverage/traceback; infrastructure/timeout/security failures never become successes. General stdin-contract inference and script repair certification are outside this additive change. The existing function contract/repair workflow remains available by analyzing functions and tests.
