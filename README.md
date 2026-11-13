# SAMYAK · Phase 2

An evidence-driven Python defect investigation and repair workbench for Yuktik. The local `ProblemStatement/Samyak_Technical_Blueprint.md` (revision 2.0) and `Hackthon.docx` define the scope. This repository preserves the Phase 1 pipeline, independently trained models and source data, and adds five connected investigation workspaces, four live source fixtures and ten bounded evidence-bearing USPs. Passing recorded tests is not a proof of universal correctness.

## Start

Requires Python 3.11+, Node **22.12+**, npm, Git and Docker Desktop/Engine running in Linux-container mode. Python 3.11 is the runner language. Internet is needed for initial dependency/image installation; normal deterministic analysis is local.

```sh
make setup
make runner
make dev
```

Open **http://127.0.0.1:3000**. API documentation: **http://127.0.0.1:8000/docs**. `make dev` starts FastAPI, one separate background worker and Next.js; Ctrl-C stops them. The API alone never processes analysis jobs. SQLite WAL metadata, append-only events and SHA-256 artifacts live in ignored `var/`.

`make train` retrains from the committed, witnessed source corpus. The checkout also includes trained RF/XGBoost artifacts, so it can analyze before retraining. Training never imports or executes corpus programs. If Docker or the fixed runner image is unavailable, jobs retain static/ML evidence and return **EXECUTION_UNAVAILABLE** for execution; there is no host-interpreter fallback.

```sh
make demo       # Phase 1 source fixtures, exact confirmation and ZIP evidence
make demo-phase2 # Full live Phase 2 circuit: four sources + witness/retrieval/twin/ledger/Shield
make test       # Backend unit/integration tests + frontend tests
make lint       # Ruff checks/format, ESLint and TypeScript
make build      # Production Next.js build
make check      # lint + backend/frontend unit/integration tests + build
make e2e        # Real Playwright workflows; starts the existing dev stack if needed
make types      # FastAPI OpenAPI → generated frontend TS types
make reproduce  # source acquisition → runner build → sandbox witnesses → training
```

Docker-dependent tests explicitly skip when the runner is unavailable. `make demo` fails closed rather than skipping its execution gate. The API, worker and frontend bind to loopback by default. This is a local development application, without public-service authentication, tenancy or quota infrastructure.

## Use the workbench

1. Paste/upload Python, or load a source fixture. Loading a fixture only populates source and authored oracle inputs; **Analyze source** runs the same pipeline as a pasted submission.
2. Watch persisted SSE stages. Inspect risk/family predictions, evidence severity, exact suspicious spans, rule qualifications and each localization signal.
3. Inspect generated cases. An annotation, successful trial or uncaught exception does **not** establish an input domain or correct output. Cases without an output oracle display `RETURNED_NO_ORACLE`.
4. For ambiguous behavior, select **Confirm output**, enter one exact JSON expectation and confirm. This creates an A-tier oracle in a **new job/test revision**. Alternatively accept the exact input domain without asserting an output; resolving only its I-tier fault receives `VALIDATED_RUNTIME_FAULT_ONLY`.
5. Inspect all candidate diffs and original/patched test matrices. The tournament rejects authoritative regressions and preserves caller tests. Export the evidence ZIP. Custom candidates can also be submitted for independent validation.

### Run ordinary Python scripts

Functions are optional. Paste `print("Hello, Samyak!")`, loops, assignments, conditions or an `if __name__ == "__main__":` program and press **Run** (⌘/Ctrl+Enter). The complete module executes as `__main__` through the same immutable-job API, separate worker and restricted Docker image. **Analyze source** (⌘/Ctrl+Shift+Enter) adds static module evidence and, when functions exist, the existing ML/input/repair workflow. A healthy script does not trigger script repair suggestions.

Expand **Standard input** for up to 8,000 characters of stdin. There is no interactive shell or package installation. The resizable **Output / Problems / Execution Trace** panel shows actual stdout/stderr, exit code, exception frames, covered executable lines, duration and timeouts. Click a traceback location to inspect that exact source line. Clear only clears the displayed output; immutable evidence remains exportable. Source, stdin or test edits invalidate prior results. Run creates a new job; it never rewrites an old report. The script suggestion is non-blocking and dismissible per submission.

`EXECUTED_SUCCESSFULLY` means the process completed; it is **not** a correctness oracle or a validated repair. Script crashes retain an unconfirmed input domain. Function-level models and frozen metrics are unchanged; script-only source shows **ML risk: Not applicable to script-only source**. Python is the supported language; `printf(...)` produces an actual Python `NameError` with a helpful C/Python explanation rather than translation.

The v1.2 API accepts `POST /v1/analyses` with `{"source":"print(input())", "mode":"SCRIPT", "stdin":"hello\n"}`. Default `mode: "ANALYZE"` automatically executes script-only submissions, including those with zero tests. `Report.script_result` carries the observation separately from function-test validation. Evidence bundles retain stdin, source and runner identity; `scripts/replay.py` replays both script and function observations in the exact image.

Rebuild with `make runner` after updating this checkout. All existing import/name allowlists remain in force; only bounded `input()` is additionally supported in the SCRIPT path. CPU/wall/RAM/PID/output limits remain fixed. Output is read-only xterm text with terminal controls removed, not a host terminal. Bounded results arrive when the worker finishes; live stdout streaming and job cancellation are not supported. Resource-forced termination can lack a full traceback/coverage; it never receives a successful verdict.

Authored tests may be provided through the JSON editor or literal source assertions. Example:

```json
[{"function":"average","args":[[1,2,3]],"expected":2.0,"has_expected":true,"tier":"A","domain":"CONFIRMED","origin":"USER_TEST"}]
```

A/B expected-behavior failures, I operational faults and C exploratory observations are separate. B currently supports an **explicitly declared sorting contract** (`property_contracts: {"function_name": "sorted_multiset"}`): output must equal the sorted input multiset. Naming alone never activates that property. Domain confirmation accepts only the selected exact input, not neighboring guesses. Timeouts, flakes, infrastructure errors, failures and unrun checks retain different states.

## Architecture and boundaries

- **Structural intelligence:** `ast`, `tokenize`, `symtable`, NetworkX; exact source spans, AST/token/function features, bounded CFG, lexical def-use and calls. Dynamic/unresolved calls are labeled. Annotations remain structural metadata, not runtime index operations.
- **ML:** separately trained RF baseline and XGBoost binary/family heads; numeric AST features and train-fitted TF-IDF. Project/problem groups are frozen before mutation and vocabulary fitting. A disjoint cohort calibrates XGBoost risk when sufficient. Model artifacts have immutable version directories, content hashes, measured cohort metrics and model cards.
- **Localization:** exposed rule strength, learned risk/family priors, graph proximity and Ochiai when failures have coverage. ML-on/off Top-1/Top-3/MRR ablation uses the same frozen candidates. No measured uplift is claimed for the current small cohort.
- **History:** TF-IDF top-k over train-only buggy→fixed pairs, normalized repair operators and smoothed edit-frequency priors. Exact self matches are excluded. Low similarity signals unfamiliarity, never a proven defect.
- **Inputs/oracles:** annotations → literal call sites → AST operations → bounded Docker trials. Explicit Hypothesis strategies generate boundaries/negative/edge cases; bounded `find` attempts shrink reproducible exception signatures. Shrinking does not transfer an exact oracle to a new tuple.
- **Repair:** formatting-preserving LibCST comparison, empty/zero guard and return-sentinel edits; surrounding functions, callers, def-use, witnesses, test revision and precedents accompany candidates. Originals are never edited. Syntax, signatures, imports, edit budget, security policy, trusted regressions and unresolved checks gate validation.
- **Execution:** fixed Linux Docker image; inputs copied over stdin into ephemeral tmpfs; non-root UID 10001, network disabled, read-only root, no mounts/socket/secrets, dropped capabilities, no-new-privileges, 1 CPU, 256 MiB RAM, 32 PIDs, per-case CPU/wall limits, suite deadline and capped output. No arbitrary package installation. Coverage is collected inside the container. Expected outputs are compared outside it.
- **Persistence/API:** Pydantic v1.2 additive contracts, SQLite WAL durable polling, single-worker OS lock, crash recovery, SHA-256 artifact verification, resumable SSE and immutable source/test/patch revisions. No Redis/Postgres.

**Docker-only isolation is development-grade.** The source allowlist restricts supported programs but is not a security boundary. Do not present this deployment as a hardened public multi-tenant sandbox. Runtime samples contain seven warmed calls per case and separate container runs; startup is excluded, but noise/order effects are not controlled enough to claim optimization. Reports correctly return `PERFORMANCE_INCONCLUSIVE` while retaining median/p95 samples and changed-line footprints (added plus removed source lines).

## Data and reproducibility

`data/source_manifest.json` pins TheAlgorithms/Python and BugsInPy metadata revisions, source hashes, licenses, extracted functions, preassigned groups, historical commits and exact acquisition exclusions. `data/seeds/` retains source and license notices. `data/corpus.json` retains verified mutations, exact fault spans, distinguishing Docker witnesses and source-only historical pairs. No historical dependencies are installed.

```sh
make sources   # Public pinned Git/raw source extraction; records inaccessible sources
make runner
make corpus    # Executes parents/mutants only in Docker; excludes unkilled/unresolved mutants
make train     # Train/evaluate; no program execution
```

The final corpus has 21 seed entries (19 unique algorithm problems), 20 historical source pairs before filtering and 111 retained pairs. 92/127 mutants had distinguishing witnesses; 35 were excluded. Rows are deduplicated and project/problem disjoint: **125 train, 4 validation, 10 calibration, 12 test**. Counts and real/synthetic results are not pooled into a flattering single score. `GUARD_REMOVAL` has only two unique training rows and is excluded from the learned family head; static guards and witnessed repair validation still work.

Three proposed seed paths were absent at the pinned revision; HTTPie bug 1/2 source revisions returned 404. Exact failures are in the manifest. QuixBugs is **not downloaded or used** in training, retrieval, prompts or tuning; external QuixBugs and separate family-holdout measurements are explicitly **NOT_EVALUATED**. This small corpus does not establish broad unseen-defect generalization. The model card/metrics expose weak cross-project behavior and no localization uplift.

The frozen corpus includes actual execution timings, so a fresh full witness run produces new evidence hashes. `make train` with the same committed corpus, pinned dependencies and fixed seed reproduces the learning inputs and model artifacts. Immutable model versions are under `data/models/versions/`; `CURRENT` selects the serving revision. Do not load untrusted joblib files.

## API and replay

- `POST /v1/analyses`; `GET /v1/analyses/{id}` and `/report`
- `GET /v1/analyses/{id}/events` (SSE with event IDs / Last-Event-ID)
- `POST /v1/analyses/{id}/tests` (new test-generation revision)
- `POST /v1/analyses/{id}/contracts/confirm` (exact A oracle)
- `POST /v1/analyses/{id}/contracts/domain` (exact input-domain acceptance)
- `GET /v1/analyses/{id}/patches`; `POST .../patches/validate`
- `GET /v1/analyses/{id}/bundle`; `GET /v1/fixtures/{name}`

Evidence bundles include source, tests, patches/diffs, job events, full results, model/runner identity and a hashed replay manifest. Extract a bundle and run:

```sh
PYTHONPATH=backend .venv/bin/python scripts/replay.py /path/to/extracted-bundle
```

Replay requires the exact recorded Docker image ID. It verifies artifact hashes and compares statuses, outputs and exception signatures; timing equality is intentionally not required.

Copy `.env.example` to `.env` to configure paths or the optional OpenAI-compatible `SAMYAK_LLM_BASE_URL`, `SAMYAK_LLM_MODEL`, `SAMYAK_LLM_API_KEY`. `make dev` loads it without shell evaluation. With all three LLM values configured, source, local context, tests, witnessed failures and short train-only precedents are sent to that endpoint; an LLM response is always an untrusted candidate. The default requires no key.

## Phase 2 workspaces and experiments

The warm light/dark Workbench uses local Geist fonts, custom Monaco themes, diagnostics/heat gutters, fullscreen, resizing, search/folding/minimap, Cmd/Ctrl+Enter to Run, Cmd/Ctrl+Shift+Enter to Analyze, and source/stdin/test revision invalidation. Fault Atlas offers bounded AST/call/CFG/def-use views, source peek and impacted callers. Contract Studio exposes real witnesses, exact confirmations/rejections and justified property checks. Repair Arena shows side-by-side diffs, elimination gates, policy and actual retrieval ablation. Model Lab & Vault shows measured binary/family/localization metrics, heuristic novelty, immutable identities and verified replay.

Experiment actions use the **same SQLite queue/worker/SSE**: `POST /v1/analyses/{id}/investigate` with `action` = `witness`, `replay`, `precedents`, `ledger`, `twin` or `metamorphic`. Exact rejections use `/contracts/decision`; sorting contracts use `/contracts/property`. `GET /v1/capabilities` reads real worker/model/runner readiness; `/timeline` exposes persisted events. All create inspectable evidence and retain uncertainty. Optional LLM configuration remains disabled by default.

```sh
cd frontend
npx playwright install chromium  # Once, for browser E2E
npm run test:e2e
```

Browser tests execute real backend jobs rather than mocked verdicts, including confirmation, regressions, abstention, graph/diff navigation, SSE recovery, witness/retrieval/twin/ledger actions, metamorphic properties and 390/1440/1920px light/dark layouts. Run Docker first; execution failures are intentionally not disguised as skipped live-demo success.

See [USP evidence inventory](docs/USP_EVIDENCE.md) and [seven-minute judge walkthrough](docs/JUDGE_DEMO.md). No new model accuracy, ML localization uplift, external QuixBugs evaluation or production sandbox security is claimed. Property/twin eligibility is intentionally bounded and unsupported paths are explicit.

See [Phase 2 handoff](docs/PHASE2_HANDOFF.md), [Phase 1 handoff](docs/PHASE1_HANDOFF.md), [requirement traceability](docs/TRACEABILITY.md) and [model card](data/models/MODEL_CARD.md).
