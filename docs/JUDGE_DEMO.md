# A seven-minute SAMYAK investigation

## Prepare once

Run `make setup`, `make runner`, then `make dev`. Open http://127.0.0.1:3000. `make train` is optional when using the checked-in model; two-phase artifacts and the original model card are retained. Before presenting, run `make demo-phase2` and `cd frontend && npm run test:e2e` against a running Docker daemon. Close old long-running jobs so the single worker is ready.

The six launcher cards load **openly labeled source fixtures** only. Every Analyze action creates a real job via `POST /v1/analyses`. There are no cached demo verdicts. Candidate order and latency can vary; select by actual verdict rather than a rehearsed candidate number. Times below are presentation targets, not measured latency statistics.

## 0:00–0:40 — establish the evidence contract

Start in the light Workbench; briefly toggle dark mode. “Samyak separates learned prediction, causal observation and repair validation. A high model score is not a confirmed defect. A green test result covers only the recorded contract.” Point to the compact workspace navigation, Monaco editor and Evidence Rail.

Load **Boundary, not a guess**. The source and six authored reference cases appear, with no result yet. Click **Analyze source** (or use Cmd/Ctrl+Enter inside Monaco). Explain that the pipeline dots and journal come from actual worker SSE events, with persisted timestamps.

## 0:40–2:00 — find and repair the boundary

When the live job completes, select the **L3** finding. The exact loop condition highlights; the rail separates rule strength, ML/family prior, graph proximity and Ochiai. Show the observed failing singleton, not just a risk gauge.

Open **Contract Studio → Find smallest witness**. Wait for `REPRODUCED`; compare the larger recorded failing input to the independently A-backed singleton. Explain the method label: smallest supported trusted case, not fabricated semantic shrinking. Click **Replay minimized witness** and inspect `MATCH`, reached lines and output mismatch.

Open **Repair Arena**. Select the actual `VALIDATED_ON_TESTS` candidate. Show Monaco's original/candidate diff (`<` to `<=` on the loop), fail-to-pass/pass-to-pass checks and elimination gates. Select a rejected candidate to contrast the evidence. “Minimality is considered only after correctness and regression gates. Runtime remains inconclusive when these tiny workloads are too noisy.”

## 2:00–2:50 — make history accountable

In Repair Arena, click **Compare retrieval**. Both arms use the same frozen suite and budget. Inspect measured first-valid rank and operator priors; do not claim improvement if the arms tie. Historical analogies in **Model Lab & Vault** show actual cosine similarity, normalized edit, origin and train-only provenance.

“Precedents influence which applicable templates are tried first; they never become output oracles. QuixBugs is absent from training, retrieval, prompts and tuning.”

## 2:50–4:00 — investigate an unknown contract

Return to Workbench, load **An unknown contract**, Analyze. Show untyped `average(nums)`, inferred list strategy and empty-input `ZeroDivisionError`. The decision must remain **INCONCLUSIVE_NO_OUTPUT_ORACLE**.

In Contract Studio, show separate tier/domain columns. First click **Confirm input domain** for the exact empty tuple: the new revision can receive **VALIDATED_RUNTIME_FAULT_ONLY** after execution, while output semantics remain unknown. The parent report is unchanged.

A candidate may propose 0. It is visibly labeled **heuristic**. Use **No** to persist a rejection without promotion; use **Edit expected → 0 → Confirm & rerun**, or **Yes, expect 0**, only after saying: “For this demo product contract, I explicitly want the empty input to return zero.” The resulting new A-oracle job validates that exact behavior. Do not imply mathematics or the model supplied this specification.

## 4:00–4:50 — catch the local repair trap

Load **The caller trap**, Analyze, then Repair Arena. Select the rejected **replace return** candidate (`None→-1`). Show the exact previously passing caller tests that now fail. In Fault Atlas, inspect **Blast radius**, affected `lookup` / `contains`, dependent tests and unresolved graph edges. Source inspection and graph selection are synchronized. Return to the boundary candidate that preserves the sentinel convention and survives.

“Context is behavioral: a locally plausible edit can violate a caller's contract. We rerun the entire available suite because the graph is incomplete.”

## 4:50–5:35 — demonstrate restraint and honest ML

Load **Correct, but suspicious**, Analyze. The redundant comparison is only a hypothesis; no authoritative failure is invented. Open **Model Lab & Vault → Novelty Radar** to inspect actual RF/XGB disagreement, outlier features and unseen AST types. Unfamiliarity lowers trust in the ML conclusion, while static/runtime investigation continues.

Show held-out counts and confusion matrices. “The retained corpus has 111 pairs. The untouched test cohort is only 12 rows. ML-off/on localization currently shows no measured uplift. We expose this because the score is an experiment, not an accuracy promise.”

## 5:35–6:25 — challenge the model and carry the proof

On a supported boundary investigation, click **Run twin challenge**. The generated redundant-parenthesis source has identical AST semantics under the restricted eligibility policy. Show actual risk delta, line overlap and repair results. This does not claim general transformation equivalence.

Click **Verify & replay**. Wait for actual hash checks and exact-image original/candidate replays to show `REPLAY_VERIFIED` / `MATCH`. Download the evidence bundle: source, diffs, tests, outcomes, model/index identities, runner digest, events, licenses and replay command. Ordinary hashes establish integrity, not authentication or correctness.

## 6:25–7:00 — close with an optional property check

If time permits, paste `def normalize(nums): return nums` as a fresh source, Analyze, and explicitly **Declare sorting contract: normalize** in Contract Studio. **Run Shield** then executes reversed-permutation/multiset and idempotence relations and exposes real violations. Explain that a function name never activates B properties.

Finish on the Repair Risk Budget: `AUTO_SUGGEST`, `REVIEW_REQUIRED` or `DO_NOT_RECOMMEND` is derived from evidence and graph uncertainty, and never auto-commits submitted code.

## Fallbacks that preserve credibility

- **Docker/image unavailable:** show the explicit `EXECUTION_UNAVAILABLE` state and static/ML evidence. Restore with Docker running + `make runner`; rerun the same source. Never use host execution or present an old ZIP as a live run.
- **SSE interruption:** the worker continues; use Reconnect. Persisted event IDs/timestamps catch up. A browser transport-abort test exercises this path.
- **No LLM key:** local deterministic templates remain functional. Repair Arena labels the local/no-key state. No external paid LLM result is claimed.
- **No authoritative oracle:** remain inconclusive or explicitly confirm an exact tuple. A heuristic candidate output is not a specification.
- **Unexpected timeout, flaky or unsupported output:** inspect the recorded state; do not relabel it as a pass. Simplify only within the openly declared supported pure-Python/finite-JSON scope.
- **Long queue:** follow real stages and inspect the previous **clearly labeled immutable revision** while waiting; do not invent progress percentages or latency numbers.

## Difficult questions

**What did ML improve?** Current small frozen localization ablation shows no uplift. Independently trained RF/XGB binary/family models, real holdouts and all signals are observable; broader benefit remains unproven.

**How do you prevent leakage?** Project/problem ancestry is split before mutation and TF-IDF fit; near/exact duplicates are filtered; precedents contain train pairs only. QuixBugs has zero pipeline exposure. Pretrained optional LLM contamination cannot be ruled out, and no external LLM was used in these tests.

**Does passing mean correct?** Only for the tested contract/property under the recorded environment. I-only validation does not establish output semantics; exact A confirmation does not define an entire domain.

**Is the runner safe for public hostile tenants?** It is restricted Docker-only, explicitly development-grade: non-root, no network, read-only root, ephemeral scratch, dropped capabilities, no host mounts/socket/secrets and finite CPU/RAM/PID/time/output budgets. Public multi-tenancy requires independent hardening and is not claimed here.

**Are the ten USPs just panels?** Each row in `USP_EVIDENCE.md` names its backend mechanism, real route/action, observable artifact and passing acceptance test. Unsupported eligibility is explicit; no positive outcome or benchmark uplift is manufactured.

## Optional — long showcase sources

Two larger fixtures exercise every workspace on realistic multi-function modules. Each takes roughly two minutes to analyze because 64 tests run against every candidate.

- **Inventory planner · correct** (18 functions, 23 authored A-oracles, a `__main__` report). All oracles pass and the script runs. Static rules still raise hypotheses, such as the strict `while lo < hi` lower bound and a guarded division. Every candidate is either rejected by a regression or left unverified, so the Risk Budget is all `DO_NOT_RECOMMEND`. The `None`-sentinel caller trap (`find_sku` → `has_sku`) is rejected even on correct code. In Contract Studio, declare a sorting contract for `insertion_sort` and run Shield to see zero violations.
- **Ledger reconciler · subtle bugs** (16 functions). The inclusive-cutoff boundary in `count_settled_by` fails two authored oracles, and the `<` → `<=` candidate validates. The `find_account` `None→-1` candidate breaks `is_known_account` callers. An empty batch crashes `average_ticket` both in the script run (real traceback) and as a replayed `[]` witness, so you can accept its exact domain. Other bugs show up only as static findings or need a confirmed output in Contract Studio: a self-comparison, a mutable default, a `None` fee path, a dropped final balance, a dropped merge tail, early interest truncation, a numerator-only guard and an off-grace late fee. The full answer key is in `backend/samyak/fixtures.py`.
