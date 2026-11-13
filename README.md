# SAMYAK

**A Python code intelligence workbench built around verifiable evidence.**

SAMYAK connects structural analysis, independently trained machine learning, generated tests and isolated execution in one investigation workflow. Inspect a suspicious line, reproduce a failure, establish an exact contract, compare repairs and export the evidence behind a decision.

Use it with a Python script, a function-based program or a single file imported from a public GitHub repository. Analysis results remain immutable; confirmations, experiments and patch validations create new job revisions.

## Quick start

### Requirements

- Python **3.11+**; the default setup command uses `python3.11`.
- Node.js **22.12+** and npm.
- Docker Desktop or Docker Engine running Linux containers.
- Git and an internet connection for initial dependency and image installation.

```sh
git clone https://github.com/DevXOmar/samyak.git
cd samyak
make setup
make runner
make dev
```

Open **[localhost:3000](http://127.0.0.1:3000)**. Interactive API documentation is at **[localhost:8000/docs](http://127.0.0.1:8000/docs)**.

`make dev` starts the API, a separate background worker and the frontend. Keep it running; Ctrl-C stops the stack. Trained models are included, so **retraining is not required** to get started. Deterministic analysis and repair work without an LLM key.

If execution is unavailable, check that Docker is running, run `make runner`, and recheck live service health in the UI. Static and available model evidence remain inspectable; execution fails closed with `EXECUTION_UNAVAILABLE`. There is no host-execution fallback. Historical reports retain their original execution status; rerunning is optional and creates a new job.

## Investigate code

1. **Open source.** Paste Python, upload a file, load a source fixture or use **Import from GitHub**.
2. **Run or analyze.** Run executes the module as `__main__`. Analyze adds structural evidence and eligible function-level prediction, test generation, localization and repair validation.
3. **Inspect the evidence.** Follow real pipeline stages, select a finding or graph node, and navigate to its exact source location.
4. **Resolve uncertainty.** Replay a case, investigate a smaller witness, confirm an exact input domain or provide an exact expected output.
5. **Compare repairs.** Inspect candidate diffs, original-versus-patched results, affected callers and regression reasons. Download a replayable evidence bundle.

**Keyboard shortcuts:** ⌘/Ctrl+Enter runs source; ⌘/Ctrl+Shift+Enter starts analysis.

### Connected workspaces

| Workspace | What it provides |
| --- | --- |
| **Workbench** | Resizable Monaco editor, file/test tabs, diagnostic markers, evidence rail, fullscreen editing and a read-only Output / Problems / Execution Trace panel. |
| **Fault Atlas** | Scoped AST, call, control-flow and def-use graphs; explainable ranked source spans; exact-line source inspection and candidate-aware impact exploration. |
| **Contract Studio** | Failure-first test investigation, inferred inputs, actual observations, oracle provenance, immutable confirmations and on-demand witness reduction. |
| **Repair Arena** | Side-by-side diffs, historical precedents, candidate elimination checks, affected-caller regressions, custom patch validation and recommendation policy. |
| **Model Lab & Vault** | Held-out model metrics, RF/XGBoost comparisons, cohort selection, localization ablation, family confusion matrices, function-risk exploration and reproducibility artifacts. |

Light and dark themes share a restrained charcoal-and-champagne palette. Source edits invalidate stale evidence. The last analysis can be restored on reload without automatically executing it again; live service capabilities remain separate from historical results.

### Scripts and functions

Functions are optional. Scripts containing assignments, loops, conditions, prints or a main guard run through the same isolated worker workflow:

```python
name = input().strip()
print(f"Hello, {name or 'SAMYAK'}!")
```

Optional standard input is bounded to 8,000 characters. Results include real stdout/stderr, exit status, covered lines, duration, timeouts and available exception frames. Traceback locations navigate back to source. Output is read-only; it is not an interactive shell. Live stdout streaming and cancellation are not currently supported.

`EXECUTED_SUCCESSFULLY` records successful execution, **not correctness**. Script-only source has no function-model risk score. Python is the supported language, and programs requiring unsupported imports or packages may not execute in the restricted runner. Source submissions are limited to 60,000 characters.

### Public GitHub import

Enter a canonical `https://github.com/OWNER/REPO` URL, inspect up to eight recommended Python files and open one in the existing editor. Recommendations use bounded static inspection and report dependency caveats and partial-tree limits.

The importer resolves the default branch to an immutable commit, preserves the selected path and provenance, and retrieves regular Python files without cloning, installing packages or executing downloaded code. No GitHub token is required. Opening a file clears unrelated fixture tests, stdin, property contracts and analysis evidence; replacing existing source requires confirmation. Importing never starts execution automatically.

**One selected file is the analysis unit.** Sibling modules and third-party dependencies are not assembled into a runnable repository. GitHub rate limits, unsupported files and unavailable dependencies are reported explicitly.

## Understand the evidence

SAMYAK keeps predictions, static hypotheses, runtime observations and validated test outcomes distinct.

- **Learned risk is not defect certainty.** Function-level RF and XGBoost models use numeric AST features and train-fitted TF-IDF. Rule severity is independent of model probability.
- **Localization is explainable.** Ranked spans expose rule strength, learned risk, family support, graph proximity and eligible Ochiai coverage. The score is a relative heuristic, not a probability; missing coverage contributes zero and is shown as unavailable.
- **A crash does not establish a contract.** Oracle tiers distinguish trusted exact expectations (**A**), explicitly justified properties (**B**), accepted-domain runtime faults (**I**) and exploratory observations (**C**). Domain confirmation applies only to the selected input tuple.
- **Proposed outputs remain unverified.** A repair candidate's output is never automatically promoted to an oracle. Witness reduction must preserve the failure class, source location and argument constraints; reduced logical failures require an applicable oracle.
- **Validation preserves uncertainty.** Verdicts distinguish `VALIDATED_ON_TESTS`, `VALIDATED_RUNTIME_FAULT_ONLY`, `REJECTED_REGRESSION`, `UNVERIFIED_SUGGESTION` and `INCONCLUSIVE_NO_OUTPUT_ORACLE`. Failures, timeouts, unrun checks and infrastructure errors remain separate.
- **Reachability is potential impact.** Caller and def-use paths help select relevant tests. Zero observed caller regressions does not mean zero risk. Passing recorded tests is not a proof of universal correctness.

### Bounded investigation tools

Train-only historical retrieval supplies actual cosine similarities, normalized edit priors and repair context, with an explicit retrieval-on/off experiment. Novelty combines historical similarity, model disagreement and feature novelty as heuristic unfamiliarity signals. Static analysis continues when learned evidence is weak.

Candidate tournaments retain syntax, applicability, security, trusted-test, caller-regression and repeatability gates. Recommendation policies return `AUTO_SUGGEST`, `REVIEW_REQUIRED` or `DO_NOT_RECOMMEND`; they never commit user code.

Advanced property checks require an explicit supported `sorted_multiset` contract and execute sorting transformations rather than assuming intent from a function name. Semantic twin experiments accept only eligible equivalence-preserving transformations. Unsupported paths return `NOT_SUPPORTED` with a reason. Ledger verification checks artifact integrity and replay evidence; hashes do not prove correctness or authenticate an author.

## Architecture and execution safety

```text
Next.js workbench
       │ REST + resumable SSE
FastAPI / Pydantic
       │ immutable jobs, events and content-hashed artifacts
SQLite WAL ── separate Python worker
                    ├─ structural analysis, models and historical retrieval
                    ├─ test inference and LibCST repair candidates
                    └─ restricted Docker runner → execution and regression evidence
```

| Layer | Implementation |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind, shadcn/ui, Monaco, React Flow/Dagre and read-only xterm output. |
| Analysis | Python `ast`, `tokenize`, `symtable`, NetworkX, Ruff and Bandit; source spans, bounded graphs and evidence-tagged rules. |
| Learning | scikit-learn RF, XGBoost, TF-IDF, versioned models, verified artifact hashes and held-out evaluations. |
| Tests and repair | Hypothesis, pytest, coverage.py, LibCST templates and optional OpenAI-compatible candidate generation. |
| Persistence | SQLite WAL, durable worker queue, append-only stage events and SHA-256 local artifacts under ignored `var/`. |

Submitted code is never executed inside the API, browser or host worker. Each suite runs in a dedicated ephemeral Linux container; individual test cases use separate subprocesses. Restrictions include non-root UID 10001, disabled networking, read-only root, dropped capabilities, no-new-privileges, no host mounts or Docker socket, no injected secrets, tmpfs workspaces, 1 CPU, 256 MiB RAM, 32 PIDs and bounded time/output. Arbitrary package installation is unsupported.

**Docker-only isolation is development-grade, not a hardened public multi-tenant sandbox.** Import/name allowlists narrow supported programs but are not a security boundary. The application binds to loopback by default and does not provide public-service authentication, tenancy or quota infrastructure.

Up to two independent candidate suites run concurrently, with unchanged per-container restrictions and deterministic result ordering. Set `SAMYAK_CANDIDATE_CONCURRENCY=1` on constrained hosts. Verified model objects are reused within the worker; submitted execution results are not persistently cached. Real stage timings and execution counters remain inspectable. See [measured performance and methodology](docs/PERFORMANCE_HANDOFF.md) for fixture comparisons and limitations.

## Models, data and reproducibility

The included corpus combines source-only BugsInPy buggy/fixed pairs with witnessed mutations of pinned, licensed TheAlgorithms/Python seeds. Project/problem lineage is split before mutation and TF-IDF fitting; historical retrieval uses training pairs only. Historical project dependencies are never installed, and training never executes corpus programs.

The committed dataset contains **111 retained pairs**, producing **125 training, 4 validation, 10 calibration and 12 test rows**. The held-out test set separates six historical and six algorithmic examples. These are small cohorts: metrics do not establish broad cross-project generalization, and there is **no measured ML localization uplift**. Underrepresented defect families are excluded from the learned family head. QuixBugs is not used in training, retrieval, prompts or tuning; external evaluation remains unevaluated.

- [Source manifest](data/source_manifest.json): pinned revisions, licenses, hashes, lineage and acquisition shortfalls.
- [Model card](data/models/MODEL_CARD.md): training scope and interpretation limits.
- [Model manifest](data/models/manifest.json): artifact identities and evaluation metadata.
- [Capability evidence](docs/USP_EVIDENCE.md): mechanisms, routes, tests and bounded support.

```sh
make sources   # Acquire pinned public sources and record inaccessible revisions
make runner    # Build the restricted execution image
make corpus    # Generate and witness mutations inside Docker
make train     # Train and evaluate from the source corpus
```

`make reproduce` runs that sequence. Training is optional for normal use. Immutable versions live under `data/models/versions/`; `data/models/CURRENT` selects the serving version. Load only trusted model artifacts. Fresh witness executions produce fresh timing evidence and may change corpus evidence hashes.

## Configuration

Copy `.env.example` to `.env` to override defaults; `make dev` loads it without shell evaluation. Keep credentials and local artifacts out of version control.

| Variable | Purpose |
| --- | --- |
| `SAMYAK_API_URL` | Local API address; defaults to `http://127.0.0.1:8000`. |
| `SAMYAK_DATA` | Job database and artifact directory; defaults to `./var`. |
| `SAMYAK_MODELS` | Model directory; defaults to `./data/models`. |
| `SAMYAK_RUNNER_IMAGE` | Restricted image built by `make runner`. |
| `SAMYAK_CANDIDATE_CONCURRENCY` | Candidate-suite concurrency: `2` by default, or `1` for sequential validation. |
| `SAMYAK_LLM_BASE_URL`, `SAMYAK_LLM_MODEL`, `SAMYAK_LLM_API_KEY` | Optional OpenAI-compatible repair provider; all three are required to enable it. |

With an LLM provider enabled, source, surrounding context, tests, witnessed failures and short training-only precedents are sent to that endpoint. Responses remain untrusted candidates subject to the same validation gates. Leave the values empty for local deterministic repairs.

## API and replay

FastAPI/Pydantic is the schema authority. Run `make types` after contract changes to regenerate OpenAPI and frontend TypeScript types.

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/capabilities` | Current worker, model and runner readiness. |
| `POST /v1/analyses` | Submit source, tests, optional stdin and execution mode. |
| `GET /v1/analyses/{id}` and `/report` | Read job state and immutable results. |
| `GET /v1/analyses/{id}/events` and `/timeline` | Resumable SSE and persisted stage history. |
| `POST /v1/analyses/{id}/tests` | Generate a new test revision. |
| `POST /v1/analyses/{id}/contracts/{confirm,domain,decision,property}` | Record exact expectations, domain decisions or supported property contracts. |
| `GET /v1/analyses/{id}/patches`; `POST .../patches/validate` | Inspect candidates or validate a submitted patch. |
| `POST /v1/analyses/{id}/investigate` | Run witness, replay, precedent, ledger, twin or metamorphic investigations. |
| `GET /v1/analyses/{id}/bundle` | Download replayable evidence. |
| `POST /v1/github/inspect` and `/v1/github/file` | Inspect a public repository and retrieve a selected commit-pinned file. |

For example, submit a script without an output oracle:

```sh
curl -X POST http://127.0.0.1:8000/v1/analyses \
  -H 'Content-Type: application/json' \
  -d '{"source":"print(input())","mode":"SCRIPT","stdin":"hello\n"}'
```

Evidence bundles contain source, tests, candidates/diffs, events, outcomes, model/runner identities and a hashed replay manifest. Extract a bundle and replay it with:

```sh
PYTHONPATH=backend .venv/bin/python scripts/replay.py /path/to/extracted-bundle
```

Replay requires the exact recorded Docker image. It verifies hashes and compares statuses, outputs and exception signatures; timing equality is not required. Runtime comparisons may remain `PERFORMANCE_INCONCLUSIVE` when equivalent workloads and reliable measurements are unavailable.

## Development and verification

| Command | Purpose |
| --- | --- |
| `make dev` | Start the local API, worker and frontend. |
| `make demo` | Execute live source fixtures, exact confirmation and evidence export. |
| `make test` | Run backend and frontend unit/integration tests. |
| `make lint` | Check Ruff formatting/lint, ESLint and TypeScript. |
| `make build` | Build the production frontend. |
| `make check` | Run lint, tests and build. |
| `make e2e` | Run Playwright workflows against the application. |
| `make types` | Regenerate OpenAPI and frontend API types. |

Install the browser once before running E2E tests:

```sh
cd frontend
npx playwright install chromium
cd ..
make e2e
```

Fixtures in [`fixtures/`](fixtures/) are source programs, not precomputed reports. They cover boundary defects, untyped runtime faults, caller regressions, unfamiliar code and larger multi-function examples through the same analysis endpoints as user submissions.

Tests cover parsing, leakage prevention, isolation, oracle uncertainty, harmful-patch rejection, model identity, graph/source navigation, import constraints and connected investigation workflows. Docker-dependent tests explicitly skip when execution is unavailable; live demos fail closed with readiness guidance rather than reporting a successful execution.
