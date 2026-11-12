# SAMYAK

**Predict defects. Trace their causes. Repair with evidence.**

**Technical solution blueprint · Revision 2.0 | Yuktik Hackathon | 13 November 2026**  
**Scope:** Python-first, extensible to Java and C++ | **Status:** revised proposed architecture and acceptance plan, not an implementation claim

> **Positioning:** Samyak is an evidence-driven code intelligence and automated program repair platform. A trained model predicts where code is risky; structural and execution analysis investigate *why*; multiple candidate patches compete; and a controlled test engine decides what can actually be verified. A fluent LLM explanation is never treated as proof of correctness.

## Executive decision

Build **one excellent Python pipeline end to end** before adding another language. Deliver all eight mandatory modules and all three advanced challenges as baseline. Then distinguish Samyak through **ten evidence-bearing innovations**: Novelty Radar, Counterexample Studio, Behavioral Contract Forge, Repair Tournament, Blast-Radius Intelligence, Metamorphic Shield, Proof-Carrying Patch Ledger, Semantic Twin Challenge, Repair Risk Budget and the **Precedent Engine**. The Precedent Engine explicitly connects historical human repairs to candidate generation; it also supplies a calibrated neighborhood signal to Novelty Radar. These are product proposals to implement and measure, not claims of previously validated research novelty.

**Non-negotiable demo contract:** for a never-before-submitted Python program, Samyak must parse code, show real AST/structure, produce a genuinely trained model score, pinpoint suspicious spans, discover at least one meaningful failing input, propose a minimal patch, run original and patched code in isolation, and show passing, failing, unrun and inconclusive checks separately. This must also work meaningfully when input code has **no tests, docstrings or type hints**: infer candidate inputs, discover runtime-fault witnesses, and offer one-click confirmation of expected behavior when necessary. It must also demonstrate a rejected repair and a case where the system abstains rather than fabricating certainty.

### Revision 2.0 decisions (integrated, not merely appended)

- **Spec-less programs:** added implicit runtime-fault oracle **I**, one-click A-tier expected-output confirmation and an explicit no-type-hint input-inference pipeline.
- **Model/domain alignment:** introduced an audited algorithmic mutation corpus alongside source-only BugsInPy pairs; independently trained **binary risk and defect-family** models; QuixBugs held out of *all* training/retrieval/selection.
- **ML accountability:** compulsory defect-line localization ablations with versus without ML priors, plus repair retrieval ablations.
- **Learning from past repairs:** train-only **Precedent Engine** with TF-IDF nearest neighbors, normalized edit scripts and template/LLM ranking; its similarity signal powers Novelty Radar.
- **Rubric clarity:** explicit severity matrix and optimization protocol (minimal patch, impacted callers, original-vs-patch runtime with repeated samples).
- **Schedule risk:** BugsInPy dependency installation is **not** needed for model training; only a few demo cases require controlled runtime execution.

---

# 1. Problem interpretation and solution boundaries

The supplied Yuktik problem statement requires learned defect prediction, semantic localization, logic analysis, repairs, generated tests, isolated execution and a dashboard. The advanced requirements—unseen defects, context-aware repairs and regression prevention—are **baseline obligations**, not optional differentiators.

### 1.1 What Samyak will and will not claim

- **Will:** assign a calibrated *estimated* defect risk to supported functions; classify supported defect families; retrieve relevant historical fixes; rank suspect locations; infer test inputs from untyped code; generate *candidate* repairs; demonstrate pass/fail behavior on executable tests; preserve provenance and uncertainty.
- **Will not:** assert that risk probability is proof a defect exists; equate a zero-test-failure patch with verified correctness; treat an uncaught exception on an out-of-contract input as proof of a semantic bug; infer correct expected output from a buggy run; claim safe execution in an ordinary unrestricted process; or treat low historical similarity as proof of a novel bug.
- **Supported at hackathon:** Python 3.11, pure-Python functions and small packages with vetted dependencies, tests/entrypoints and well-defined inputs. Python's dynamic dispatch, reflection, native extensions and environment-dependent behavior are handled as limitations when analysis cannot establish a reliable result.
- **Explicit stretch:** Java via tree-sitter/JUnit, C++ via tree-sitter/Clang and sanitizers, repository-scale cross-module graph analysis, CodeBERT embeddings and deeper symbolic execution. No multi-language badge until one complete cross-language repair-and-validation workflow works.

### 1.2 Three kinds of evidence

1. **Prediction evidence:** independently trained ML estimates plus training metadata, calibration and novelty flags.
2. **Causal evidence:** rules, AST/CFG/def-use links, execution traces, coverage and minimized failing examples.
3. **Repair evidence:** historical repair precedents (advisory), patch diff, original-versus-fixed outputs, preserved tests, generated tests, regressions, safety checks, measured runtime delta and replayable execution manifest.

Keep these separate in the API and UI. Their combination makes Samyak credible; collapsing them into one unexplained 'AI confidence' does not.

# 2. End-to-end platform architecture

```text
                        SAMYAK — CODE INTELLIGENCE PLATFORM
 ┌────────────────────── USER EXPERIENCE ────────────────────────────┐
 │ Next.js + Monaco editor  |  File/ZIP upload  |  Demo case library │
 │ Risk map | Graph explorer | Repair diff | Test console | Evidence  │
 └──────────────────────────────┬────────────────────────────────────┘
                                │ FastAPI / WebSocket or SSE
 ┌──────────────────────────────▼────────────────────────────────────┐
 │ ORCHESTRATOR: immutable analysis job + content hashes + statuses  │
 │                                                                    │
 │  AST/tokens/CFG/def-use ──► RF/XGB risk + defect-family classifier│
 │            │                         │                              │
 │            │            train-only TF-IDF precedent index          │
 │            ▼                         ▼                              │
 │  semantic rules + dependency graph + evidence-based localization  │
 │            │                                                       │
 │            ▼                                                       │
 │  input inference + graded oracles + generated boundary/edge tests │
 │            │                                                       │
 │            ▼                                                       │
 │  sandboxed original run + implicit fault oracle + shrink/replay    │
 │            │                                                       │
 │            ▼                                                       │
 │  precedent-ranked templates + grounded LLM patch candidates       │
 │            │                                                       │
 │            ▼                                                       │
 │  sandbox repair runs + regressions + runtime/patch optimization    │
 │            │                                                       │
 │            ▼                                                       │
 │  report + failure witnesses + provenance / export                 │
 └──────────────────────┬────────────────────────────────────────────┘
                        │ queue / isolated worker protocol
             ┌──────────▼───────────┐  ┌────────────────────────────┐
             │ Sandboxed runner     │  │ PostgreSQL + object store  │
             │ gVisor preferred     │  │ Jobs, models, tests, diffs,│
             │ no network/secrets   │  │ traces, hashes, manifests  │
             └──────────────────────┘  └────────────────────────────┘
```

**Design principle:** parsing and prediction are side-effect-free services; user code is never imported or executed by the FastAPI process, training worker, database process or frontend. Only the separately hardened runner executes it.

### 2.1 Services and contracts

| Service | Responsibility | Artifact / gate |
|---|---|---|
| Ingestion and analysis API | Validate uploads, assign immutable job IDs, expose status and reports | Source hash, language/version, size/extension limits |
| Structural engine | Python `ast`, `tokenize`, `symtable`, LibCST spans; lightweight CFG, def-use and calls | Function facts, source-map, graph JSON |
| Model service | Independently train and load risk + defect-family models; calibration and uncertainty | Risk estimates, family distribution, cohort/model IDs and novelty signal |
| Logic and localization engine | AST patterns, partial data flow, suspicious branches, test coverage, spectra | Findings with spans, severity, evidence and limits |
| Contract/test engine | Evidence-ranked input inference, existing tests, implicit runtime faults, boundary cases, Hypothesis, explicit one-click confirmation | Candidate input schema, A/B/I/C oracle ledger, confirmed assumptions and minimal witnesses |
| Precedent + repair engine | Training-only TF-IDF retrieval of human/synthetic bug-fix edits; ranked templates; grounded LLM patch proposals | Similarity/evidence trail, normalized edit prior and candidate diffs |
| Validation scheduler | Execute original and patches independently in sandbox; compare outcomes and controlled runtime | Verdict, test matrix, failures, median/p95 runtime and patch footprint |
| Evidence and presentation | Immutable analysis report, live progress, downloadable patch/test bundle | Replay manifest and source-to-result links |

**API boundary:** FastAPI/Pydantic define versioned JSON contracts; a worker queue (Redis + RQ/Celery, or durable database polling for a smaller build) runs expensive jobs; PostgreSQL stores job metadata and object storage stores code, traces and patches with short retention. Use one schema authority rather than ad hoc frontend/backend definitions.

# 3. Complete mandatory-requirement traceability

Every row below is **P0 baseline**. A feature is complete only after the specified observable acceptance check, not when its UI is present.

| PS module | Concrete Samyak implementation | Judge-facing acceptance evidence |
|---|---|---|
| **M1 Code Intelligence** | Python AST, tokenizer; per-function spans; nesting, operators, branches, loops, calls; lightweight CFG/def-use graph | Show AST summary, token count, function list and inspectable edges for submitted code |
| **M2 Defect Prediction** | Independently train RF/XGBoost binary defect risk and supported defect-family prediction on real BugsInPy bug/fix pairs **plus verified algorithmic mutations**; TF-IDF + AST features | Show frozen lineage splits, separate real/synthetic/external metrics, family prediction, calibrated risk and model contribution to localization |
| **M3 Semantic Bug Localization** | Function/family ML priors + exact mutation/diff fault spans + static rules + graph + spectrum-based line ranking when tests run | Show line-level ground truth on the mutation holdout and **Top-1/Top-3 with vs without ML prior** |
| **M4 Logical Error Detection** | Boundary/index checks, loop off-by-one, wrong comparisons, zero divisors, empty-input assumptions, unsafe calls, return inconsistencies and observed crash/timeout/assertion faults | Show precise rule IDs, real runtime witnesses, domain-of-input qualification and safe non-bug countercases |
| **M5 Automated Program Repair** | Human-fix precedent retrieval, normalized edit-operator priors, typed LibCST templates and grounded LLM-generated diffs | Show retrieved past fixes, why particular edits ranked first, ≥2 candidates where available and minimal successful diff |
| **M6 Test Generation** | Infer inputs with or without type hints; existing/call-site examples, AST constraints, bounded probes, Hypothesis strategies; A/B/I/C oracles and one-click confirmation | Show source of inferred domain, minimized fault input, user-confirmed expected result and no-oracle fallback |
| **M7 Repair Validation** | Identical sandboxed original/patch suites, regressions, timeouts, nondeterminism and runtime measurement | Original fault resolved; old tests preserved; bad patch rejected; before/after runtime measured on stable comparable inputs |
| **M8 Intelligence Dashboard** | Risk + family scores, explicit severity policy, suspicious lines, comparable historical fixes, oracle provenance, diff/test/runtime comparison and evidence export | One job timeline including `OBSERVED_RUNTIME_FAULT`, confirmed A-oracle cases, unresolved checks and optimization stats |

### 3.1 Advanced requirements are baseline—not USPs

| Advanced challenge | Baseline design | Acceptance test |
|---|---|---|
| **Unseen defect prediction** | Bug-lineage and algorithm-problem disjoint training/evaluation, held-out projects, held-out mutation families, no QuixBugs training or precedent lookup and measured novelty | Show external QuixBugs assessment and report family/project misses, coverage, novelty and reliability rather than a cherry-picked example |
| **Context-aware repair** | Supply callers/callees, def-use/preconditions, existing tests, *retrieved historical fixes*, inferred domain assumptions and observed failures; reject edits violating known behavior | Show a false friend in similar past code, a harmful local fix rejected by affected callers and a passing context-aware alternative |
| **Regression prevention** | All available authoritative tests, contract/implicit tests, eligible generated tests and affected-dependent tests rerun for each patch; judge-only hidden tests stay outside repair context | Show fail-to-pass **and** pass-to-pass, new crashes/hangs, timeout/error states and rejected candidate |

# 4. Deep technical design: how the eight modules work

## 4.1 Structural code intelligence

Parse without executing imports. `ast.parse()` yields tree nodes with line/column locations; `tokenize` retains lexical signals; `symtable` helps understand scopes; LibCST produces formatting-preserving edits. Construct an **Intermediate Code Intelligence Graph (ICIG)** with node types: `Module`, `Function`, `Statement`, `Variable`, `Condition`, `Call`, `Test`, `Finding`. Edges: `CONTAINS`, `CALLS`, `DEF_USE`, `CONTROL_NEXT`, `TRUE_BRANCH`, `FALSE_BRANCH`, `COVERED_BY`, `DEPENDS_ON`. Start with intraprocedural flow and explicit static calls; label dynamic or unresolved calls as unknown rather than pretending the graph is complete.

Extract features at function level: length, parameters, cyclomatic-complexity proxy (decisions + 1), maximum nesting, `if`/`for`/`while` counts, exception handlers, comparisons, boolean operators, mutation/subscript operations, divisor operations, null/empty checks, unresolved names, branching and return-path consistency, fan-in/fan-out (where resolvable), rule counts and normalized token n-grams. Store precise `start_line/end_line/start_col/end_col` so ranking can be mapped back to source.

## 4.2 Learned defect prediction: two genuine ML tasks, two complementary data domains

**Independent training path:** parse sources without running project dependencies → extract numeric AST/CFG indicators and normalized code-token TF-IDF → independently train `RandomForestClassifier` baseline and `XGBClassifier` on **binary defect-risk** labels → train a separate **multiclass defect-family head** from verified mutation operator labels plus confidently annotated real fixes → select hyperparameters on grouped training/validation → calibrate risk on a disjoint calibration partition → evaluate on untouched grouped real-world, algorithmic and external cohorts.

A legitimate `defect_family` prediction is not just a static-rule name. The classifier consumes code features and learns to classify e.g. `BOUNDARY_COMPARISON`, `CONDITION_NEGATION`, `GUARD_REMOVAL`, `ARITHMETIC_OPERATOR`, `INDEX_OFFSET`, `RETURN_VALUE` and `OTHER/UNSUPPORTED`. Include a `CLEAN` category only where clean labels are credible. Train a single binary + multiclass multitask setup only if evaluation justifies the complexity; two simpler models are safer for a hackathon. Never train a claimed category using one or two unreliable examples; report `UNKNOWN_FAMILY` when below confidence/novelty threshold.

**Source-domain handling:** BugsInPy supplies real historical bug/fix source snapshots and edit spans (extractable statically); an **Algorithmic Mutation Corpus** supplies numerous controlled buggy/fixed function pairs with exact operator/family/line labels. The latter fixes the domain mismatch between project-level BugsInPy and short QuixBugs-like demo functions. Do **not** mix domain scores into one flattering number: report `REAL_BUGSINPY`, `SYNTHETIC_ALGORITHM`, `FAMILY_HOLDOUT` and `EXTERNAL_QUIXBUGS` performance separately, with a pooled operational model only after assessing source-weight sensitivity.

Use train-fitted TF-IDF as the required semantic signal. CodeBERT/GraphCodeBERT remains an optional frozen-feature experiment; the independently trained Samyak classifier is RF/XGBoost. Never allow split-leakage through vocabularies, scalers, calibration, hyperparameter selection, near-duplicate variants, precedent retrieval or LLM demonstration examples.

A function score is `P(training-defined defect label | features, model/version)`, not an unconditional crash probability. Program score is `max(function risk)` labeled **highest modeled function risk**; avoid `1 − ∏(1−p)` over correlated functions. UI must show model family, score calibration, training domains and out-of-domain warning; if inference is too novel, present a lower-trust prediction or abstain on ML conclusion while still running independent static/dynamic checks.

**Non-negotiable ML contribution experiment:** retain the exact same rules, graph, coverage, candidate budget and tie-breaking; compare localization Top-1/Top-3/MRR with `ML_PRIOR_ENABLED` versus `ML_PRIOR_DISABLED` on a frozen defect-line holdout. Add `FAMILY_PRIOR_ENABLED` versus disabled if volume permits. A meaningful ML module must improve a measurable downstream decision, not only paint a gauge.

## 4.3 Semantic localization and logical detection

Create deterministic rule detectors with `rule_id`, preconditions, evidence span, confidence tier and false-positive notes. First-family coverage: `INDEX_BOUNDARY`, `LOOP_OFF_BY_ONE`, `EMPTY_COLLECTION`, `DIV_ZERO`, `CONDITIONAL_INVERSION_CANDIDATE`, `NONE_DEREFERENCE`, `UNSAFE_EVAL_EXEC`, `DANGEROUS_DESERIALIZATION`, `MUTABLE_DEFAULT`, `INCONSISTENT_RETURN`. Some categories (condition inversion especially) are **hypotheses**, not factual defects until behavioral evidence supports them.

When executable tests exist, gather branch/line coverage for passing and failing cases and compute **Ochiai** suspiciousness for line `l`: `failed_cover(l) / sqrt(total_failed * (failed_cover(l) + passed_cover(l)))`. If the denominator is zero, mark the spectral score unavailable. Fuse signals using a transparent, initially hand-tuned ranker for candidate spans: ML function risk, **learned defect-family prior**, deterministic rule strength, graph proximity to failing paths and Ochiai. Compare exactly the same system with and without the ML contributions on known mutation/diff fault spans, and show retrieval/edit priors separately from risk prediction. Distinguish `MODEL_RISK`, `RULE_WARNING`, `OBSERVED_RUNTIME_FAULT`, `BEHAVIORALLY_REPRODUCED` and `CONFIRMED_BY_TRUSTED_ORACLE` in result metadata. `OBSERVED_RUNTIME_FAULT` requires a reproduced crash/hang/assertion but is not automatically a proven *contract violation* if the input domain is unknown.

## 4.4 Repair synthesis

Produce **multiple candidate patches**, never silently mutate the uploaded program. First use **Precedent Engine edit-operator frequencies** to order safe, provenance-rich LibCST templates for common well-scoped defects (loop boundary, guard on empty input, corrected comparison only when an oracle clarifies the intent). Then request up to 2–3 bounded LLM patch candidates, supplying the exact suspicious spans, surrounding function, relevant caller/callee summaries, tests, observed failures, contract constraints and the top *training-only* human-fix precedents (each explicitly labeled as analogous, not authoritative). Demand a unified diff or structured edit with changed-line bounds; refuse unrelated file or dependency changes.

All candidates must pass: patch application → syntax/compile → import/allowlist checks → isolated tests → regression and security checks → **stable runtime comparison and minimal-diff tie-break** → patch ranking. Retrieve precedents once per immutable analysis job; never pull a reference patch from external benchmark/test split. An LLM's self-assessment never counts as validation. If no candidate passes, the correct output is **unresolved**, with the best reproducible counterexample.

## 4.5 Test generation for **unknown, untyped and test-less programs**

The common judge input has **no tests, no type hints and no declared specification**. Samyak must still produce useful evidence. The crucial separation is **input-domain discovery** (what inputs to try), **observed execution failure** (what actually happened), and **output correctness** (what behavior should have happened). They are not interchangeable.

### 4.5.1 Evidence-tiered oracle ledger

| Tier | Examples | What it can establish | Guardrail |
|---|---|---|---|
| **A — explicit / user-confirmed** | Supplied expected outputs, authored tests, benchmark reference, explicit contract; **one-click confirmation for one exact input/output pair** | Correctness/failure **for the exact covered case** | User confirmation is scoped to that tuple; do not pretend it defines the entire function |
| **B — independently justified relation** | A trusted reference algorithm, mathematically grounded property, sound metamorphic relation | Violation or preservation of the specified **property** | Record assumptions and domain; candidate property inferred from naming alone is not B |
| **I — implicit runtime-fault oracle (new)** | Uncaught `IndexError`, `ZeroDivisionError`, `AttributeError` from `None`, `AssertionError`, nontermination/timeout under suitable budgets | Reproducible **operational failure** on an input established or confirmed to be **in contract** | A crash can be intended rejection of invalid input; a timeout can be environment/slowness rather than infinite loop |
| **C — heuristic / exploratory** | LLM-proposed expected value, candidate-repair agreement, code-name guess or original-program output | Prioritization and questions for the user | Cannot certify a semantic fix or veto a patch as a trusted oracle |

`I` is deliberately *not* a weaker spelling of A: an uncaught exception may show a clear problem without showing which output is correct. Keep **oracle origin**, **domain status**, **assertion source** (`USER_TEST`, `SOURCE_ASSERT`, `GENERATED_ASSERT`), **repeatability**, **resource budget** and **observed fault type** as separate fields. A source assertion may itself encode a faulty assumption; an uncaught assertion only becomes a verified contract violation when that assertion is trusted. Timeouts need controlled reruns (pinned seeds, ample yet finite budgets and comparison with a known-safe baseline); report `TIMEOUT_OBSERVED`, not an unprovable universal claim of infinite looping.

**Failure policy when no oracle exists:** An in-domain crash is actionable and may guide repair immediately, but an I-only fix cannot assert that the new output is correct. If the input type/domain is only *hypothesized*, label the output `OBSERVED_RUNTIME_FAULT / DOMAIN_UNCONFIRMED` and prompt for confirmation or investigate related call sites; do **not** invent `CONFIRMED_BUG`. If no fault and no trustworthy output contract emerges, show structured static predictions and `INCONCLUSIVE_NO_OUTPUT_ORACLE`, never a fake green fix.

### 4.5.2 Deterministic input inference hierarchy (not dependent on hints)

Build `InferredParameterSchema` **without importing target code**. Every candidate constraint carries `evidence_source`, `confidence`, `accepted_domain?` and a human-readable reason.

1. **Explicit annotations/docstrings/contracts** if present, producing Hypothesis `st.from_type` where supported. An annotation alone does not establish full value constraints, e.g. sortedness.
2. **Existing test call sites** (`pytest` invocations and `assert f(...)`) and **other source call sites** (`f([1,2], 4)`), mined statically. Derive observed value types, shapes, domains, tuple arity and relationships such as array + target. Tests and call sites may disagree; preserve alternatives instead of forcibly narrowing to one.
3. **AST operation constraints:** `len(xs)`, `for x in xs`, `xs[i]` suggests a sized/indexable or iterable parameter; arithmetic/comparisons suggest numeric candidates; `.get` suggests a mapping; `s.split()` suggests string; `if x is None` suggests optionality; `i < len(xs)` suggests an integer index relationship. Infer **candidate** types, not guaranteed types or semantic preconditions.
4. **Safe bounded trial execution inside the hardened sandbox:** generate small deterministic candidate pools (empty/nonempty lists, integers around 0/±1, short strings, dicts, `None` where plausible); execute within per-case resource and side-effect budgets, recording `TYPE_REJECTED`, `ACCEPTED_EXECUTION`, `RUNTIME_FAULT`, `TIMEOUT` separately. No trial runs in the API process. Candidate inputs that crash are **observations**, not proof they are valid inputs.
5. **Human refinement:** an editable “Expected input shape” chip (e.g. `list[int], int; list sorted; duplicates allowed`) confirms the contract domain without code edits. If ambiguity remains, retain multiple labeled candidate domains and request confirmation only when needed for a verdict.

**Strategy construction:** convert evidence into **explicit** Hypothesis combinators—not `st.from_type` for unannotated arguments. For example `st.lists(st.integers(-10,10), max_size=20)`, `st.integers(-10,10)`, tuples and shared/derived strategies for dependent parameters; add targeted `[]`, singleton, duplicates, off-by-one indices, zero divisor, very long/empty strings and boundary values **only within established/confirmed domains**. Hypothesis automatically shrinking is used once a stable failure predicate exists; keep its exact seed and minimized example. Limit combinatorial explosion using a per-function input budget, maximum shapes and a visible coverage breakdown.

### 4.5.3 One-click behavior confirmation (interactive oracle promotion)

For an untyped `binary_search(nums, target)` that returns `-1` for `([7],7)`, Samyak may surface a **candidate** expected value from a heuristic/reference interpretation, but **must not assert it as correct**. Show:

> **Observed:** `binary_search([7], 7) → -1`  
> **Confirm expected behavior:** Should `binary_search([7], 7)` return `0`? **Yes / No / Edit expected / Ignore**

`Yes` persists an **A-tier USER_CONFIRMED** single-case oracle containing exact serialized input, expected output, reviewer and timestamp; `Edit expected` records the user's different value. `No` or `Ignore` leaves it heuristic. Confirmation triggers a **new versioned validation run**, not retroactive editing of old results. Scope confirmation to the chosen behavior: it does not imply that `nums` must always be sorted, that the function's entire behavior is known or that neighboring heuristic tests become authoritative. Use a separate confirmation for input-domain assumptions if required.

### 4.5.4 Minimal-witness logic and negative tests

Always attempt: in-contract empty/singleton/boundary partitions, negative/adversarial data with **explicit domain tags**, in-contract bad-operation triggers (divide by zero if denominator zero allowed), duplicate/sorted/reverse alternatives where relevant, and seeded Hypothesis shrinking. Store `test_origin`, `strategy`, `input_schema`, `domain_status`, `oracle_tier`, `expected`, `observed`, `failure_signature`, `minimized_from` and `confirmation_id`. Negative tests outside the contract are **robustness observations**, not correctness regressions.

**Strict stop rule:** LLM-proposed expected values and analogous repairs are not oracles. Failing assertions inserted by the repair model are not proof. A green repaired run with no A/B/I-backed failure resolved stays `UNVERIFIED_SUGGESTION`, even if heuristic cases pass. Resolving only I-tier unexpected failure qualifies for **operational-fault validation**, not proof that the new return value is semantically correct.

## 4.6 Repair validation, regression policy and the meaning of optimization

Run original and repaired code in **identical** isolated images, package versions and seeds. Freeze a test manifest before patch generation. The hard gates are: patch applies and compiles; no introduced security/API risk; every previously passing **A-tier** test stays passing; independently justified B-tier relations are preserved under their assumptions; reproducible **in-contract** I-tier operational faults are resolved without new faults; and affected-caller plus held-out tests do not regress. Generated heuristic C-tier examples are explanatory only.

**Verdict taxonomy:** `VALIDATED_ON_TESTS` (at least one A/B expected-behavior failure repaired and all applicable hard gates pass), `VALIDATED_RUNTIME_FAULT_ONLY` (an in-contract I-tier crash/hang eliminated without a trusted output oracle; output semantics still unknown), `OBSERVED_RUNTIME_FAULT` (original execution event, domain confirmed or unconfirmed separately), `REJECTED_REGRESSION`, `REJECTED_SYNTAX`, `REJECTED_SECURITY`, `UNRESOLVED`, `UNVERIFIED_SUGGESTION`, `INCONCLUSIVE_NO_OUTPUT_ORACLE`, `INCONCLUSIVE_TIMEOUT`, `FLAKY`, and `SANDBOX_ERROR`. No smoke test counts as verification merely because the process exited `0`. Distinguish an intentionally raised exception defined by the contract from an unexpected crash.

**Interpretation of rubric “Automated repair and optimization” (15 marks):** optimization means **minimal defensible source edit, minimal behavioral blast radius, reasonable execution cost and evidence of runtime effect**—not a claim that every bug fix improves time complexity. The Tournament uses **hard correctness/regression/safety gates first**. Among equally validated candidates, prefer (1) smaller normalized AST/CST edit distance and changed-line count, (2) smaller affected-call-graph radius, (3) lower stable runtime/resource overhead, (4) lower LLM cost. A larger patch is permitted when a smaller one fails semantics.

**Runtime comparison protocol:** use the same accepted in-domain workload and runner image; warm both variants where appropriate; alternate randomized run order, perform multiple measured iterations, and report `n`, median and p95 wall time, max RSS where available, sample variability, `delta_ms` and `delta_percent`. Separate sandbox startup/compilation time from *function runtime*. Do not compare a crashing original on its failing input against a successful patch and call the difference a speedup; run comparable **formerly passing inputs** and newly passing input cases in separately marked bands. Short/noisy cases get `PERFORMANCE_INCONCLUSIVE` rather than a made-up faster/slower label. Track test throughput and patch footprint as secondary optimization measures.

Repeat surprising failing/passing results to flag flaky tests. Never give the repair LLM access to frozen external/hidden evaluation tests. Record unexecuted tests with reasons; timeout/OOM/harness failure is a non-passing state, never silently skipped.

## 4.7 Dashboard semantics and **explicit severity policy**

The interface is an investigation workspace, not an inflated ML gauge. Display separate `model_risk`, `predicted_defect_family`, `severity`, `fault_evidence`, `oracle_tier`, `domain_status`, `precedent_similarity`, runtime metrics and replay status. Severity is a **human-readable impact policy**, never `severity = model probability`.

| Severity | Policy / typical examples | Evidence and qualification |
|---|---|---|
| **CRITICAL** | Reachable arbitrary code execution, unsafe untrusted deserialization or comparable high-impact exploitable operation | Require supported reachability/attack surface or a confirmed unsafe sink; otherwise label **potential critical** and show the unverified condition |
| **HIGH** | Confirmed wrong result, unexpected crash, in-contract assertion failure or reproducible serious hang for a legitimate input; major invariant break | Requires A/B/I evidence with confirmed domain (or demonstrably unsafe path) |
| **MEDIUM** | Plausible off-by-one, boundary/logic flaw, unsafe assumption or suspected incorrect condition not yet behaviorally confirmed | Rule/model/precedent hypothesis; no unsupported high-severity claim |
| **LOW** | Noncritical robustness/style/maintainability finding, redundant check or low-impact issue without observed wrong behavior | Some low-level findings may be informational rather than defects; report separately where sensible |

Add a distinct **evidence-status badge**: `HYPOTHESIS`, `RUNTIME_FAULT_DOMAIN_UNCONFIRMED`, `FAULT_CONFIRMED`, `VALIDATED_RUNTIME_FAULT_ONLY`, `PARTIALLY_VALIDATED`, `VALIDATED_ON_TESTS`. A defect may be HIGH impact yet LOW model confidence; those are different axes. Show exact spans, minimal witness, accepted contract, retrieved precedent edits and before/after median runtime in the comparison view.

# 5. Dataset and scientific ML evaluation plan

## 5.1 Dataset inventory, source-only preprocessing and legal/quality guards

| Source / cohort | Usage | Split and execution policy |
|---|---|---|
| **BugsInPy** (real projects) | Real historical buggy/fixed source snapshots, real edit scripts, function-level binary labels of varying confidence | **For training, source checkout + AST/diff extraction only**. No project environment reconstruction required; reproduce just a few chosen executable cases for demos/validation |
| **TheAlgorithms/Python** (correct seed implementations) | Algorithmic functions to mutate into categorized defects; optional seed tests | Pin repo revision and licenses; audit function correctness and independent tests before treating parent as `CLEAN` |
| **MBPP** (alternative/additional seed implementations) | Small problem solutions, associated descriptions/tests, optional structured positive/negative pairs after mutation | Honor official task-level splits; only use permitted **training** tasks as mutation seeds, never benchmark test tasks if reporting them as unseen |
| **HumanEval** (optional) | High-quality short function seeds with contracts/tests, **only if isolated to an approved seed partition** | Widely exposed code-evaluation dataset; avoid in the initial corpus if test contamination/LLM familiarity cannot be audited; never treat as a fresh external benchmark after training on it |
| **QuixBugs** | **Fully held-out external Python defect prediction/localization/repair assessment** | Zero rows in training, TF-IDF vocabulary fit, precedent index, few-shot examples, templates extracted from examples or model-selection feedback. Freeze before first evaluation; disclose public-benchmark pretraining contamination limits |
| **Authored negative/adversarial holdouts** | Correct-but-suspicious code, ambiguous contracts, misleading names, invalid input and source-hint drift | Group-disjoint and undisclosed to the LLM during repair; measure false alarms and incorrect user-confirmation prompts |

BugsInPy is **not an environment-reproduction prerequisite for training**. Parse pinned buggy and fixed revisions statically. Identify the diff hunk, map it to function spans, derive buggy-side and fixed-side feature rows and store the edit script. If a change spans imports/multiple functions, keep a traceable cross-file case or exclude it with a reason rather than label unrelated functions as clean. `fixed` means “this reported bug was patched”, not “the project is entirely bug-free”. Runtime reproduction is a separate, optional audit tier. Its exact exclusions and non-executable samples are reported.

## 5.2 Algorithmic Mutation Corpus — the real bridge to unseen short programs

**Pipeline:** (1) select and license-audit correct seed function; (2) tokenize/parse with precise spans; (3) apply one controlled mutation to create a buggy candidate; (4) record operator, changed AST node, source spans, parent ID and source hash; (5) syntax-check and filter trivial non-compiling mutations; (6) where seed tests/reference outputs are available, execute correct and mutant in sandbox on bounded generated/known inputs and require a **distinguishing witness**; (7) mark candidates without a distinguishing witness `UNVERIFIED_MUTANT`—usable for exploratory analysis, **not** as high-confidence defect supervision; (8) deduplicate AST/token near twins and export aligned `clean ↔ buggy ↔ expected edit` records.

**Suggested mutation families:** `LT_TO_LTE / LTE_TO_LT`, `EQ_TO_NE`, `CONDITION_NEGATION`, `AND_TO_OR`, `RANGE_BOUND_SHIFT`, `INDEX_PLUS_MINUS_ONE`, `REMOVED_EMPTY_GUARD`, `DIVISOR_GUARD_REMOVAL`, `ARITHMETIC_OPERATOR_SWAP`, `RETURN_VALUE_CHANGE`, and `WRONG_VARIABLE_REFERENCE` where syntactically and semantically meaningful. Balance mutation categories and avoid obvious artifacts (e.g. a magic token inserted in all positives). More synthetic examples are not automatically better; separate **mutant kill rate**, equivalent/stillborn mutants and family-level distribution. Exact mutation spans provide an *injected-defect* ground truth; they do not guarantee that every mutation causes observable harm until confirmed by a test.

This corpus supplies: **(a) trained defect-family labels**, **(b) exact modified-line ground truth for localization**, **(c) more algorithm-like samples similar in style to short judge submissions** and **(d) repair edit scripts**. Keep `MUTATION_SYNTHETIC` distinguishable from `BUGSINPY_REAL` in every dataset row/report; do not assert human-world generalization based on mutant-only performance.

## 5.3 Leakage-resistant splits and train-only Precedent Engine index

1. Freeze a source manifest: `sample_id, source_dataset, source_revision, project_id, problem_id, lineage_group_id, bug_id, version, language, function_span, injected_span, true_family, label_confidence, input_contract_source, split, source_sha256, fixture_execution_status`. Include `edit_script`/`edit_span` only for allowed paired samples.
2. Split **before** tokenizer TF-IDF fitting, feature scaling, synthetic mutation generation, calibration and neighbor indexing. All versions of a bug, algorithm seed, near-duplicate solution and its mutation descendants live in the **same group**. Apply hash/syntactic fingerprint checking across split boundaries; remove/reassign collisions and report them. For MBPP, respect its published task partitions where relevant.
3. Keep an untouched real-project holdout, a problem-disjoint algorithm holdout, a **held-out mutation-family** challenge (unknown operations may map to `OTHER/UNKNOWN`) and fully external QuixBugs. Report domain/sample counts per partition; stratify *groups*, not raw descendants, when possible.
4. Fit `TfidfVectorizer` **only on train samples**. Build the **Precedent Engine** from **train-split positive buggy→fixed pairs only**, with record IDs, buggy-function TF-IDF vectors, defect family, diff hunks and normalized edit operations. No validation/calibration/test pair or QuixBugs record enters the index—even if it is publicly accessible.
5. Deduplicate leaked historical commit twins and near-identical bug-fix pairs; group by lineage and similarity cluster. Use the same frozen vectorizer to query held-out code, not a separately refit vocabulary. Limit prompts to licenses and content policies; prefer short edit summaries to copying entire external source files.
6. Train and calibrate risk/family thresholds on designated folds; novelty abstention thresholds can use **train/validation-only** distance distributions with a clearly defined novelty validation set. Frozen external holdout is never used to choose thresholds or repair templates.
7. A published QuixBugs case can already be familiar to a pretrained LLM. Zero **team pipeline** leakage is enforceable; zero **foundation-model** pretraining contamination is not guaranteed. Disclose benchmark exposure, provide at least one original unseen live example and avoid reporting QuixBugs performance as proof of unseen-for-all-models novelty.

## 5.4 What is evaluated, and how to prove ML matters

| Study | Required quantitative outputs (populate with measured values only) |
|---|---|
| Binary prediction | PR-AUC, ROC-AUC, recall, precision, F1, confusion matrix, positive prevalence and per-domain sample counts |
| Defect-family head | Macro-F1, per-family precision/recall/support, confusion matrix, `UNKNOWN/ABSTAIN` rate, real-vs-mutation cross-domain behavior |
| Calibration | Brier score/reliability diagram and threshold risk coverage, with calibration cohort explicitly separate |
| Localization | Fault-line Top-1/Top-3 hit, MRR and effort-to-first-fault on exact mutant spans and real diff spans **separately** |
| **ML prior ablation (non-negotiable)** | `RULES+GRAPH+COVERAGE` vs `+BINARY_ML` vs `+BINARY+FAMILY_ML`; identical candidate budget/test suite; report ΔTop-1/Top-3/MRR and CI where possible |
| Repair grounded by history | `TEMPLATES+LLM WITHOUT PRECEDENTS` vs `+PRECEDENT_RANKING` vs `+FEW_SHOT_PRECEDENTS`; valid rate@K, trusted repair pass rate and mean candidate cost |
| Retrieval | Top-k defect-family match, normalized edit-operator recall@k, nearest-neighbor similarity and retrieval latency; retrieval is not patch correctness |
| External unseen | QuixBugs (completely held out), original blind cases; precision/recovery/failure rates and any public-benchmark contamination caveat |
| Mutation quality | Valid/rejected/equivalent/unkilled mutant counts, actual behavioral kill rate, family distribution and dedup group counts |
| Test/oracle effectiveness | In-domain implicit fault yield, incorrect-oracle rate, percent of untyped submissions with a viable strategy, confirmation-to-A rate, shrunk witness size, oracle-free inconclusive rate |
| Validation and optimization | Fail-to-pass, pass-to-pass, regressions, unresolved, runtime median/p95 and delta on comparable workloads, patch-line/AST-edit footprint |
| Resources | End-to-end p50/p95 latency, sandbox setup cost, RAM, tokens and local/paid model usage |

**Minimum reproducible baselines:** (A) `RULE_ONLY`; (B) RF with numeric structural features; (C) TF-IDF-only XGBoost/RF; (D) combined TF-IDF+AST XGBoost; (E) combined binary + family head; (F) same with precedent ranking; optional frozen CodeBERT if spare compute. Pre-register the exact splits and metrics before showing results. Report domain shifts and failures, not just best-case score.

# 6. Ten meaningful innovations beyond the baseline

Each proposal contains a distinct mechanism, a visible judge demonstration, a metric and a failure boundary. Implementing all ten fully is ambitious; sections 12–13 prioritize the most demonstrable subset while keeping the rest in a documented roadmap.

## USP 01 — Novelty Radar: calibrated prediction with a right to abstain

**Why beyond baseline:** unseen-defect detection is mandatory; Samyak adds a *reliability layer* that decides when a familiar-model prediction is trustworthy enough to display prominently. **Mechanism:** reuse the **train-only Precedent Engine's nearest-neighbor cosine similarity** (low match = unfamiliar historical context), combine it with ML feature-space density, ensemble disagreement and calibration; produce `IN_DISTRIBUTION`, `NOVEL_PATTERN`, or `INSUFFICIENT_EVIDENCE`. A low historical similarity is *not* itself a bug, nor evidence that a defect family is truly new: abstain from an overconfident **ML/precedent-based conclusion** while continuing rule detection, implicit-oracle execution and test generation. Tune novelty thresholds without touching QuixBugs.

**Demo:** submit a trained-domain off-by-one case with matching precedents, then a structurally unusual generator/closure case whose nearest eligible precedent is weak. The latter causes an ML-prior abstention while runtime checks continue. **Measure:** false-positive rate versus prediction coverage, OOD AUROC where labels exist, neighbor-distance distribution and repair outcomes on novel samples. **Boundary:** unfamiliar source is often correct; never mark it buggy solely by low similarity.

## USP 02 — Counterexample Studio: the smallest input that proves a behavioral failure

**Why beyond baseline:** test generation is mandatory; this turns it into *explanatory failure reconstruction*. **Mechanism:** generate boundary/property cases, capture execution traces, cluster failures by exception/output signature and shrink a failure using Hypothesis shrinking or a bounded delta-debugging strategy. Bind failing input → reached branch → suspicious AST/CFG span → error/explanation.

**Demo:** on a trusted reference-backed search problem, a long failing input shrinks to a singleton; on a spec-less input, a crashing witness shrinks while the domain is flagged as confirmed or unconfirmed. **Measure:** percentage of eligible defects yielding a trusted minimal witness, median witness size reduction and replay success. **Boundary:** shrinking only preserves the tested predicate; the minimal example is not proof of unique root cause.

## USP 03 — Behavioral Contract Forge: generate the *specification clues*, not just tests

**Why beyond baseline:** ordinary test generation produces inputs; the Forge builds and tags *checkable behavior contracts*. **Mechanism:** infer parameter shapes from type hints **when available**, then test/internal call sites, AST operations and sandbox-only bounded trial execution. Build explicit Hypothesis strategies; collect implicit runtime-fault oracles (I tier), A-tier authored/user-confirmed expectations, B-tier sound relations and C-tier guesses. A one-click input/output confirmation promotes only the agreed tuple to A. If neither an in-domain fault nor trustworthy output behavior can be established, return `INCONCLUSIVE_NO_OUTPUT_ORACLE`.

**Demo:** submit code without hints/tests; inspect inferred `list[int] × int` candidates; replay a minimized fault; click “Yes, this should return 0” to create a one-case A oracle and rerun validation. **Measure:** untyped-strategy coverage, I-tier in-domain fault yield, A-promotion rate, false-oracle rate and tests per confirmed witness. **Boundary:** one click proves one expectation, not an entire program contract.

## USP 04 — Repair Tournament: competitive patch selection instead of first-answer bias

**Why beyond baseline:** repairing code is mandatory; the Tournament generates *diverse patch families* and runs a bounded evidence-driven competition. **Mechanism:** order 1–2 deterministic CST edits using **Precedent Engine edit frequencies** and propose up to 2–3 LLM diff candidates grounded by retrieved human fixes; deduplicate semantically identical patches; prefilter syntax; execute all candidates on identical tests; score with a lexicographic policy: authoritative regressions first, then resolved trusted failures, then property/coverage results, edit footprint, dependency blast radius and measured runtime cost on comparable workloads. Never trade a trusted regression for a prettier patch.

**Demo:** show three candidates—one syntax-invalid, one fixes a visible example but breaks empty input, one passes the trusted suite. Show a transparent elimination bracket. **Measure:** validated repair rate@K, mean candidate count, tokens per valid repair and rejected-regression rate. **Boundary:** a winner is *validated on tested behavior*, not universally correct.

## USP 05 — Blast-Radius Intelligence: downstream behavioral impact, not just nearby lines

**Why beyond baseline:** context-aware repair is mandatory; this adds an explicit **impact model** to determine *which other code and tests must be challenged*. **Mechanism:** walk call and def-use graph from edited statements to direct callers, affected return values and dependent tests; create a bounded risk-weighted test plan. Unknown dynamic edges are visibly flagged, not dropped silently.

**Demo:** fix a function's return convention while a caller depends on a sentinel value; a seemingly good local patch is blocked by a caller regression. **Measure:** additional regressions caught over file-local-only testing, selected-test recall and test budget saved versus running every check first. **Boundary:** Python's runtime dispatch limits static completeness; always run the entire available authoritative suite before final acceptance when feasible.

## USP 06 — Metamorphic Shield: test correctness even when expected outputs are scarce

**Why beyond baseline:** generated edge cases are required; the Shield tests **relations between executions** where exact outputs are unknown. **Mechanism:** choose relation templates based on function contract: permutation invariance for multiset counts, idempotence for normalization, round-trip encode/decode, monotonicity for cumulative aggregates or preservation of sorted multiset. Transform an input and compare outputs under a declared relation; tag relation provenance and assumptions.

**Demo:** correct-looking candidate passes a handful of examples but violates 'sort twice equals sort once' or 'sorting preserves multiplicities'. **Measure:** confirmed new failures discovered, independent relation coverage and false-positive rate. **Boundary:** never apply a relation universally; for example, a ranking algorithm may intentionally be order-sensitive.

## USP 07 — Proof-Carrying Patch Ledger: every green badge has replayable evidence

**Why beyond baseline:** the PS asks for validation results; this makes evidence **portable and audit-ready**. **Mechanism:** bind SHA-256 of original source, candidate diff, model ID, runner image digest, testcase list, seeds, commands, structured output and verdict into a deterministic `repair_manifest.json`. Link each claim in the UI to its exact test record, environment and logs. Optionally hash-chain events for tamper evidence; ordinary hashes alone are not authentication.

**Demo:** export a patch/test bundle, replay it with the same image, and demonstrate that modifying the patch changes its content digest. **Measure:** replay match rate, shareable artifact completeness and untraceable-verdict count (target zero). **Boundary:** replays depend on pinned dependencies and platform; cryptographic integrity is not a formal proof of correctness.

## USP 08 — Semantic Twin Challenge: pressure-test patches under equivalent rewrites

**Why beyond baseline:** regression testing ordinarily checks more inputs; this checks if the *repair decision is brittle to superficial code representation*. **Mechanism:** apply controlled semantics-preserving transformations where valid—renaming local variables, harmless parenthesization, equivalent loop syntax in bounded examples—then compare model rankings and candidate repair behavior. A transform must be independently verified or restricted to syntax-preserving transformations before it becomes a trusted twin.

**Demo:** rename `arr` to `values` and rearrange equivalent conditions; ask whether the same underlying bug is localized and repaired. **Measure:** ranking stability, repair success under transformations and counterexamples to model shortcut learning. **Boundary:** reflection, name inspection, scoping and side effects can make 'cosmetic' rewrites semantic; do not blindly claim equivalence.

## USP 09 — Repair Risk Budget: choose what to automate, review or decline

**Why beyond baseline:** repair generation and validation are required; this introduces a **risk-aware deployment gate**. **Mechanism:** combine test trust, novelty/OOD, diff surface, dynamic-call uncertainty, new dependency changes, severity, affected-graph radius and coverage gap into explicit policy bands: `AUTO_SUGGEST`, `REVIEW_REQUIRED`, `DO_NOT_RECOMMEND`. No automatic production commit or push by default; the developer reviews candidate patches.

**Demo:** a tiny, well-tested boundary patch is surfaced as low-risk; a patch that changes authentication logic with weak tests is visibly escalated or declined. **Measure:** inappropriate auto-suggestion rate, high-risk abstention precision and developer-review reduction. **Boundary:** policy bands are operational heuristics, not absolute guarantees of safety.

## USP 10 — Precedent Engine: learn how historical bugs were **actually repaired**

**Why beyond baseline:** a historical dataset should affect not only the predicted defect score but **which repairs Samyak tries**. This is instance-based, inspectable repair intelligence mined from bug-fix history—not “ask an LLM to remember the right patch.”

**Mechanism, end to end:**

1. During source-only preprocessing, collect eligible **train-split** buggy→fixed pairs from BugsInPy and verified algorithmic mutations. Align changed functions and record ground-truth diff spans, source lineage and confidence.
2. Normalize buggy function token/AST text (`NAME` normalization should preserve meaningful API/operator signals) and fit the **same train-only TF-IDF vectorizer** used for compatible semantic features. Store sparse buggy vectors and an edit representation: `COMPARISON_LT_TO_LTE`, `ADD_EMPTY_GUARD`, `MOVE_BOUND_CHECK`, `INDEX_SHIFT`, `REPLACE_RETURN`, `CHANGE_BOOLEAN_OPERATOR`, etc. Store the *actual concrete diff* separately, with license and provenance.
3. At inference, retrieve top-`k` **training-only** neighbors by cosine similarity; filter self/near-duplicate submissions and unsupported edits; expose similarity, same/different inferred family and a short human-readable “what changed.” Similar-looking code is not proof the same patch is valid.
4. Compute a smoothed operator prior such as `P(edit=e | neighbors) = (α + Σ_i similarity_i · 1[edit_i=e]) / (|E|·α + Σ_i similarity_i)` for the supported operator vocabulary. Rank **applicable** LibCST templates by prior × safe-precondition checks; do not blindly paste neighbors' patches.
5. Supply up to 2–3 vetted neighbor edit summaries/short diffs as **flagged precedent examples** to the LLM along with local context, failure witness and contract. The LLM may propose a candidate, but only sandboxed tests decide acceptance. If neighbors disagree, display that disagreement instead of manufacturing one “correct” repair.
6. Reuse **nearest eligible neighbor similarity** in Novelty Radar. A low maximum similarity triggers *historical-pattern unfamiliarity* and more exploratory validation/ML abstention; it must **not** stop independent static checks or imply that the code is defective.

**Judge-facing illustration (schematic, not measured):** `4 similar historical bugs`; their edit distribution is `3× LT→LTE`, `1× add empty guard`; show original historical snippets/abstract edit summaries and similarities; watch Samyak try the relevant comparison-bound template first and reject it if regressions appear. The displayed counts and similarities must come from a real built index—never hard-code this example into the demo as if measured.

**Metrics:** edit-operator Recall@3, retrieved-family match@k, difference in repair success@K and candidate/runtime/token cost with and without precedents, plus novelty risk-coverage. **Failure modes:** false friends (semantically different algorithms), license-sensitive source reuse, retrieval of an external benchmark, synthetic edit dominance and code-style bias. Report real-only versus synthetic-only precedent ablations. **Scope:** retrieval augments analysis, it never certifies a semantic fix.

### 6.1 Why these are differentiators rather than renamed requirements

The required platform **predicts, localizes, repairs and validates**. Samyak additionally (1) quantifies when prediction should abstain, (2) produces smallest replayable failure witnesses, (3) maintains graded test-oracle provenance, (4) compares repair candidates under a transparent competition, (5) identifies downstream change impact, (6) derives independent metamorphic checks, (7) packages verifiable evidence, (8) tests semantic robustness under controlled rewrites and (9) places policy constraints on automation, while (10) makes historical buggy→fixed examples directly inform repair order and explanations. Each has its own test and measurable failure mode.

# 7. Mathematical decision policy, novelty and honest confidence

**Risk:** `p_f = calibrator(model(features_f))` for a pinned training cohort/model; if calibration is insufficient, label it uncalibrated. **Program:** `max_f p_f` means *highest modeled function label risk*, not the probability of a program-wide failure. **Family:** `P(family | features)` is a different output with its own confusion matrix/abstention and is trained from verified mutation/fix labels.

**Localization:** compute Ochiai on eligible executed tests and combine **function risk + family prior + rules + graph relevance + coverage** to rank fault spans. Publish per-signal contributions, and show the compulsory ablation `same ranker without ML` → `with ML`. Without failing traces report `STATIC_ONLY` (or `RUNTIME_FAULT_ONLY` if a crashing path was reached) instead of hallucinating coverage evidence.

**Historical retrieval:** for normalized train-only TF-IDF vectors, `sim(q,b_i)=cosine(v_q,v_i)`. Nearest-neighbor similarity can govern **novelty abstention** and weight **edit-operator priors**; it must not enter the trusted-oracle column. Align the retrieved edit family to the local AST and verify template applicability before trying it.

**Patch acceptance:** at least one reproducible A/B/I **in-contract** failure must be resolved, with zero introduced hard-gate regressions and safe syntax/execution; use `VALIDATED_RUNTIME_FAULT_ONLY` if I is the sole trustworthy oracle, never imply output correctness. If fault input's contract is unconfirmed, classify as a reproduced runtime observation or unverified patch until confirmed. Rank only admissible patches, lexicographically: (1) no authoritative regression, (2) trusted failures resolved, (3) minimal AST/changed-line edit and blast radius, (4) stable runtime overhead, (5) candidate execution/LLM expense. A measured runtime gain is *optional*, correctness is not.

**Confidence labels:** `Measured` (actual execution or benchmark), `Derived` (sound relation under stated assumptions), `Predicted` (ML), `HistoricalAnalog` (similar past edits), `Heuristic` (rule/LLM/candidate domain), `Unavailable` (not checked). Keep `domain_status` and `oracle_tier` separate from the certainty label. Results and exports must preserve these distinctions.

# 8. A concrete demonstration: binary search off-by-one

**Uploaded program (intentionally defective):**

```python
def binary_search(nums: list[int], target: int) -> int:
    left, right = 0, len(nums) - 1
    while left < right:  # BUG: one-element search window is skipped
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Known contract for the benchmark-backed run:** `nums` is sorted ascending; return an index of `target` if present, else `-1`. **Trusted failing witness:** `nums=[7], target=7`; original returns `-1` but the expected answer is `0`. **Candidate patch:** change `while left < right` to `while left <= right`. This candidate must be executed, not accepted merely because the rule looks right.

| Generated or supplied case | Expected / oracle | Original | Patch outcome to verify |
|---|---|---|---|
| `([], 7)` | `-1`, reference contract | `-1` | `-1` |
| `([7], 7)` | `0`, reference contract | `-1` | `0` |
| `([7], 8)` | `-1`, reference contract | `-1` | `-1` |
| `([2, 4, 7], 7)` | `2`, reference contract | `-1` | `2` |
| `([2, 4, 7], 4)` | `1`, reference contract | `1` | `1` |
| `([4, 2, 7], 2)` | Outside sorted-input contract | Not a valid correctness check | Do not claim a defect from this input |

Values in this table describe the **expected demonstrator behavior by code inspection**, not results of a completed Samyak implementation. Capture the real runner output and any discrepancies before presenting metrics or a success badge.

**Demo/domain warning:** This is an algorithmic toy, not a typical BugsInPy project function. Samyak's **algorithmic mutation training cohort** is specifically added so the live score is not solely extrapolated from real-project functions. Still display its domain/novelty tag, **never train on this exact function/near-twin or QuixBugs version**, and assess binary-search-like examples in a source/problem-disjoint evaluation. If this fixture was authored/rehearsed, clearly label it `DEMO_FIXTURE`, not frozen blind test evidence.

**Judge sequence:** upload → AST and feature view → trained risk/family scores + algorithmic cohort label → Precedent Engine neighbors/edit distribution → `while` condition highlighted → failing singleton input and path witness → compare two/three diffs → patch validation and runtime delta → external regressions → export reproducible patch ledger. Demonstrate two separate oracle modes: (a) an **A-tier reference-backed** instance from a benchmark fixture, and (b) the *same untyped function without a supplied spec*, where `([7],7) → -1` is only suspicious until a human confirms `0` via one click.

### 8.1 A second spec-less demo: implicit runtime fault

```python
def average(nums):
    total = sum(nums)
    return total / len(nums)
```

With inferred candidate type `list[number]`, `average([])` reproduces `ZeroDivisionError` in a sandbox. **But** whether `[]` belongs to the intended function contract is unknown from this source alone; display `OBSERVED_RUNTIME_FAULT / DOMAIN_UNCONFIRMED`. A human can confirm empty input should be supported, promoting the input-domain assumption; the system still needs an expected output policy (zero? exception? `None`?) before claiming a **correct return-value repair**. A template `if not nums: return 0` is a *candidate*, not a proven fix without that policy. If the user says empty input is invalid and exceptions are intended, the runtime fault becomes an intentional-domain-rejection observation rather than a confirmed defect.

**Why both demos matter:** A/B oracles can prove wrong *outputs*; I-tier runtime faults work on unseen code with no expected-output reference, subject to contract validity; C-tier guess plus user confirmation can create a precise A-case. No general solver can infer arbitrary intended behavior from syntax alone.

# 9. Product experience and dashboard information architecture

**Visual direction:** restrained premium engineering workspace; off-white or warm-charcoal surfaces, restrained blue/amber semantic accents, crisp monospaced code and rich data visualization. Avoid gimmicky AI-chat-first UX. Monaco code editor occupies the left; evidence and graph occupy the right; test and diff panels follow the developer's investigation flow.

| Screen | What the user sees | User action |
|---|---|---|
| **Workbench / Upload** | Paste code, upload `.py`/vetted ZIP; optional tests/spec; Python version and execution limits | Analyze genuinely untyped/test-less code or load a labeled fixture |
| **Intelligence Overview** | Highest function risk and family, training-domain/novelty tag, severity policy, model ablation and evidence status | Inspect ML vs non-ML localization, abstention and exact training cohort |
| **Fault Atlas** | Source heat map, suspicious spans, call/def-use graph, failing line coverage and witness | Select a line to inspect related conditions and tests |
| **Counterexample Studio** | Candidate inferred input schema, A/B/I/C provenance, fault witnesses, shrink history, stdout/stderr and traces | Replay, confirm input domain or click Yes/Edit to promote **one** expected-output tuple to A |
| **Precedent + Repair Tournament** | Top-k historical train-only fixes, edit frequencies, candidate diffs, why each survived/failed and dependency impact | Inspect retrieved human/synthetic analogs, compare, pin, reject, export or request review |
| **Regression Lab** | Original vs candidate matrix, pass-to-pass/fail-to-pass, new faults, median/p95 runtime and changed-line count | Rerun same workloads; inspect statistical/noise caveats and per-case logs |
| **Evidence Vault** | Model artifact/version, dataset split, runner digest, manifest, patch, tests and report | Download JSON/Markdown and unified diff |

**Accessibility and clarity:** keyboard controls, color-independent pass/fail labeling, line-level jump links, legible diffs, no green badge for an unexecuted test, and explicit `Not run`/`Inconclusive` rather than zeroes.

# 10. Proposed technical stack and repository structure

| Layer | Recommended implementation | Reason |
|---|---|---|
| UI | Next.js + TypeScript + Monaco Editor + React Flow/Cytoscape + Tailwind | Fast workbench, source annotation and graph exploration |
| API | FastAPI + Pydantic + SSE | Python orchestration, documented contracts, visible job progress |
| Static analysis | Python `ast`, `tokenize`, `symtable`; `networkx`; LibCST for edits | Reproducible structural facts and formatting-preserving patches |
| ML | scikit-learn, XGBoost, SciPy; risk + multiclass family model; TF-IDF; optional frozen CodeBERT | Trained baselines in both real-project and short-algorithm domains with ablations |
| Testing | pytest, Hypothesis, coverage.py/pytest-cov; AST/call-site input-inference layer; Bandit/Ruff | Untyped strategy generation, implicit-oracle fault discovery, shrinking, coverage and safety checks |
| Repair LLM | Swappable LLM provider through structured JSON/diff adapter | Context-based patch suggestions without owning verdicts |
| Jobs and data | Redis/RQ (or Celery) + PostgreSQL + object store / local dev directory | Async execution, immutable reports, bounded artifacts |
| Isolation | Dedicated Linux runner; gVisor `runsc` preferred; hardened containers only as bounded development fallback | Separation of trust between web app and user code |
| Reproducibility | pinned lockfiles, train-only precedent indexes, dataset manifests, SHA-256 artifacts, CI | Strict external holdouts, auditable retrieval and replayable repair evidence |

```text
samyak/
  apps/web/                    # Next.js workbench and dashboards
  services/api/                # FastAPI, job state, endpoints
  services/analyzer/           # AST, CFG, data flow, rules, localization
  services/ml/                 # features, binary/family training, evaluation, calibration
  services/precedents/         # train-only indexed bug/fix edits, retrieval and novelty signals
  services/testgen/            # type/callsite/AST input inference, A/B/I/C oracles, shrinker
  services/repair/             # templates, LLM adapter, tournament
  services/runner/             # sandbox protocol; never import user code in API
  packages/contracts/          # Pydantic schemas + generated TS types
  datasets/manifests/          # source-only BugsInPy, mutations, groups, splits, licenses
  benchmark/                   # frozen cohort splits, QuixBugs blind eval, ablations and results
  examples/demo_cases/         # labeled fixtures with trusted outputs
  docs/                        # architecture, threat model, evaluation
  infra/                       # runtime images and Compose for development
  tests/                       # unit, integration, adversarial, E2E
```

**Indicative API:** `POST /v1/analyses` (upload/reference) → `202` + job; `GET /v1/analyses/{id}`; `GET /v1/analyses/{id}/events` (SSE); `GET /v1/analyses/{id}/findings`; `GET /v1/analyses/{id}/precedents`; `GET /v1/analyses/{id}/input-inference`; `POST /v1/analyses/{id}/contracts/confirm` (**creates an immutable A-case/versioned run**); `POST /v1/analyses/{id}/tests/generate`; `POST /v1/analyses/{id}/repairs`; `POST /v1/repairs/{candidate_id}/validate`; `GET /v1/analyses/{id}/report`; `GET /v1/analyses/{id}/bundle`. Jobs have immutable inputs; confirmations/reruns create new run IDs.

# 11. Report contract and lifecycle

A complete result **must** include every expected PS output even when some data are unavailable. Use structured status rather than fake values.

```json
{
  "schema_version": "2.0",
  "analysis_id": "example-only",
  "status": "NOT_RUN",
  "language": "python",
  "source_sha256": "<computed-from-submission>",
  "model": {
    "risk_model_id": "xgb-risk-v2",
    "family_model_id": "xgb-family-v1",
    "trained_by_team": null,
    "source_cohorts": ["BUGSINPY_REAL", "MUTATION_SYNTHETIC"],
    "training_manifest_sha256": "<computed>",
    "calibration_status": "AVAILABLE_OR_UNAVAILABLE"
  },
  "program_risk": {
    "value": null,
    "aggregation": "MAX_FUNCTION_RISK",
    "meaning": "model-label risk, not probability of program failure",
    "novelty_status": "NOT_RUN"
  },
  "findings": [{
    "id": "F-001",
    "classification": "LOOP_OFF_BY_ONE",
    "predicted_family": "BOUNDARY_COMPARISON",
    "severity": "MEDIUM",
    "function": "binary_search",
    "line_start": 3,
    "line_end": 3,
    "evidence_status": "HYPOTHESIS",
    "domain_status": "UNCONFIRMED",
    "explanation": "Singleton search window appears skipped",
    "model_risk": null,
    "counterexample_ids": ["T-002"]
  }],
  "input_inference": {
    "status": "NOT_RUN",
    "candidate_signature": "list[int], int",
    "evidence_sources": ["AST_OPERATIONS"],
    "confirmation_required": true
  },
  "historical_precedents": {
    "index_id": "train-only-tfidf-v1",
    "neighbors": [],
    "edit_operator_prior": {},
    "similarity_is_oracle": false
  },
  "generated_tests": [{
    "id": "T-002",
    "input": [[7], 7],
    "expected": null,
    "observed": null,
    "oracle_tier": "C",
    "expected_value_proposal": 0,
    "provenance": "HEURISTIC_PENDING_ONE_CLICK_CONFIRMATION",
    "domain_status": "UNCONFIRMED",
    "confirmation_id": null
  }],
  "repairs": [{
    "id": "P-001",
    "unified_diff": "<candidate-diff>",
    "precedent_ids": [],
    "validation": "NOT_RUN",
    "fail_to_pass": null,
    "pass_to_pass": null,
    "regressions": null,
    "unresolved_findings": ["F-001"],
    "optimization": {
      "changed_lines": null,
      "normalized_ast_edit_distance": null,
      "original_runtime_median_ms": null,
      "patched_runtime_median_ms": null,
      "runtime_delta_percent": null,
      "performance_status": "NOT_RUN"
    }
  }],
  "execution": {"sandbox": "NOT_RUN", "runner_digest": null},
  "limitations": ["Illustrative schema, not actual model or runner output"]
}
```

### 11.1 State machine

`UPLOADED → PARSING → PREDICTING → RETRIEVING_PRECEDENTS → LOCALIZING → INFERRING_INPUTS → GENERATING_TESTS → BASELINE_EXECUTION → AWAITING_OPTIONAL_CONFIRMATION → GENERATING_PATCHES → VALIDATING → REPORT_READY`. Confirmation creates a new analysis revision/run; unattended jobs may bypass the optional pause and finish with uncertainty flags. Each stage supports `FAILED`, `SKIPPED_WITH_REASON`, `TIMED_OUT` and `CANCELLED`. Preserve stage timestamps, source and index/model hashes, runner resources and test/oracle versions. Only a genuine completed worker result can set a successful verdict.

# 12. Restricted execution and threat model

The submitted program and any generated test or patch are **untrusted code**. Merely calling `subprocess` with a timeout, running code inside an API process, or placing it in a default Docker container is not an adequate production sandbox.

**Minimum controlled runner:** dedicated Linux worker/host isolated from API and database; per-job ephemeral filesystem; non-root UID; read-only root FS with bounded tmpfs scratch; no outbound network; no inherited secrets, Docker socket or host mounts; drop Linux capabilities; `no-new-privileges`; restrictive seccomp/AppArmor where compatible; cgroup CPU/RAM/PID quotas; disk/file-size/output limits; wall-clock cutoff and process-group kill; vetted prebuilt dependency images only; symlink/path traversal protections; runtime telemetry and cleanup. Prefer gVisor (`runsc`) or a microVM for actual hostile multi-tenant code. If only ordinary Docker is available in the hackathon environment, explicitly label it **development-grade isolation** and never expose it publicly as secure arbitrary-code execution.

**Attack and failure inventory:** infinite loops, fork bombs, memory floods, filesystem reads, network exfiltration, dynamic imports, malicious package install hooks, hostile test fixtures, prompt injection in comments/docstrings, LLM-suggested risky edits, dependency mismatch, nondeterministic/flaky tests, poisoned training samples, benchmark/test leakage and model overconfidence.

**Controls:** reject ZIP traversal, cap source/file count and **trial-execution budgets**, forbid arbitrary dependency installation, set strict prompt boundaries (code/comments are data, not LLM instructions), validate structured diffs, scan patches for risky new calls/dependencies, keep external reference/hidden tests and held-out precedent edits out of LLM context, sign/authenticate exported manifests only if keys are actually deployed, make uploads private with retention/deletion policy, and rate-limit concurrent jobs. Measure runtime only within hardened workers, always distinguish a resource cutoff from proven infinite-loop behavior, and do not treat automatically generated invalid-input faults as in-contract vulnerabilities.

# 13. Build order, milestones and minimum demonstration gates

**Sequencing update:** the **static-source BugsInPy + mutation corpus** and **untyped input inference/implicit oracle** should be on the critical path, not late additions. The Precedent Engine's first version is straightforward after the training manifest and TF-IDF pipeline exist; it is the most efficient new flagship USP.

| Phase / priority | Deliverable | Acceptance gate |
|---|---|---|
| **P0 — Vertical slice + untyped operation** | Paste `.py` → AST/rules → inferred candidate inputs → sandbox fault run → candidate diff → original/patch execution → real dashboard | Works without tests/hints for a reproducible runtime failure; records domain qualification and inconclusive outcomes truthfully |
| **P1 — Source-only dataset & real ML** | Download/pin BugsInPy buggy/fixed revisions **without dependency setup**; generate verified algorithmic mutation pairs; freeze grouped splits; train RF/XGBoost binary + family heads | Model and family labels exist; no cross-split ancestry; real/synthetic/test counts published; QuixBugs excluded from training |
| **P2 — Precedent + measured localization** | Train-only TF-IDF fix index, normalized edit scripts, nearest-neighbor retrieval, rule/graph/ML line ranker and ML-off ablation | Live historical neighbor and edit distribution; measured Top-1/Top-3/MRR **with vs without ML** |
| **P3 — Oracles + context-aware repair** | A/B/I/C ledger, inferred Hypothesis strategies, shrinking, one-click A promotion, safe templates + LLM alternatives, affected callers | Untyped test-less case → witness → human confirmation → valid patch; bad patch rejected; new run is immutable |
| **P4 — Optimization + proof** | Repair Tournament, original/patch runtime comparison, changed-line/AST edit measurements, evidence manifest and severity policy | Visible before/after median/runtime variance with `INCONCLUSIVE` where noisy, and complete evidence export |
| **P5 — Innovative extensions** | Novelty Radar from precedent similarity + model uncertainty, Meta Shield, Blast Radius, semantic twins and repair risk policy | At least three complete and measured USPs (prefer Precedent Engine, Contract Forge, Repair Tournament) and a real external blind evaluation |

**Time-saving design:** build training pairs and fixed/buggy function features from source alone; **only** run three carefully selected demo cases (e.g. known-contract wrong result, no-spec crash, multi-function regression). If runtime reproductions for broader BugsInPy later succeed, add them as higher-confidence audits without blocking ML training.

### 13.1 Parallel ownership for a four-person team (adjust to actual roster)

| Workstream | Owner focus | Deliverable boundary |
|---|---|---|
| **ML + dataset research** | Source-only BugsInPy extraction, verified mutation corpus, RF/XGB binary+family models, splits/ablations | Frozen models, `model_card.md`, evaluation manifest and lineage report |
| **Analysis + localization** | AST/CFG/rules, spans, coverage, ML-localization ablation, precedent retrieval index | `analyzer` + `precedents` services with known-line ground truth |
| **Repair + execution** | Untyped strategies, A/B/I/C oracles, LibCST edits, runner/measurements and repair validation | Reproducible runtime faults, confirmation reruns and before/after test/perf matrix |
| **Product + integration** | Next.js workbench, severity table, precedent display, confirmation UX, job API and export | Live E2E for spec-less and benchmark cases with traceable evidence |

Integrate continuously on shared schemas. Avoid giving each developer a separate speculative microservice that only merges on demo day.

### 13.2 Definition of done before presentation

- A real source upload reaches a finished report in a repeatable fresh environment.
- Real AST/token/graph extraction is visible (not LLM text pretending to be parsing).
- Independently trained RF/XGBoost **binary and family** artifacts and evaluation notebook/script exist; source-only BugsInPy preprocessing works; algorithmic mutation family ground truth and frozen held-out metrics are reproduced.
- A target finding has correct function and source line; **ML-off vs ML-on localization** is measured on grouped defect-line holdout, not just claimed.
- Generated boundary and negative cases include A/B/I/C oracle and domain provenance; a no-hints/test-less input obtains explicit candidate Hypothesis strategies and observed runtime outcomes.
- Original and patched code really execute in the restricted runner, with timeouts/OOM isolated; one-click confirmation creates a versioned A-case for a spec-less wrong-output example.
- At least one trusted failing case is repaired; all previously passing authoritative tests remain passing; **runtime delta and patch footprint** are measured on comparable input workloads.
- A deliberately wrong fix triggers a regression rejection. An undecidable case remains inconclusive.
- All eight PS outputs exist in the downloadable report, including severity and optimization evidence. All three advanced challenges have acceptance evidence; training-only historical fixes are visibly used in a repair decision.
- No fixture results masquerade as live results; QuixBugs is excluded from model fitting, precedent lookup and prompt exemplars; dataset/demo case exposure and LLM-pretraining uncertainty are disclosed.

# 14. Rubric-driven evidence plan (100/100 coverage target)

This is a **coverage strategy**, not a predicted judge score.

| Judge criterion | Points | What to put in front of judges |
|---|---:|---|
| Dataset engineering and preprocessing | 10 | Source-only BugsInPy pairs, algorithmic mutation/family/line labels, manifest, clone/equivalent filtering, lineage isolation |
| Code representation and feature extraction | 15 | Live AST, token counts, CFG/def-use diagram, typed feature vector, exact source mapping |
| ML model development and prediction | 20 | Binary + defect-family RF/XGBoost, real/synthetic/QuixBugs cohort metrics, calibration and **ML-on/off localization ablation** |
| Semantic bug localization | 15 | Ranked functions/statements, rule/graph/coverage/ML contributions, exact mutation-line ground truth and measured Top-k uplift |
| Automated repair and optimization | 15 | Train-only historical edit priors, context-aware candidate diffs, minimal verified change, **original vs patch runtime** median/p95 and honesty about noise |
| Test generation and regression validation | 15 | Untyped input inference, **implicit in-contract fault oracle**, one-click confirmation, shrinking, A/B/I/C ledger, pass-to-pass/fail-to-pass |
| Innovation and technical demonstration | 10 | **Precedent Engine + Novelty Radar + Contract Forge** (and Tournament where implemented), with ablations, evidence export and honest abstention |
| **TOTAL** | **100** | Complete end-to-end evidence, no static mock verdicts |

### 14.1 Acceptance test pack (required in CI / demo rehearsal)

**AT-01** malformed code is rejected without execution. **AT-02** AST/token source spans map to editor lines. **AT-03** pinned source-only BugsInPy extraction works without project dependency installs. **AT-04** clean/buggy versions and mutation descendants share lineage groups. **AT-05** QuixBugs samples never enter train, TF-IDF fit, precedent index, threshold tuning or few-shot prompts. **AT-06** verified mutation emits correct defect family and exact line; unverified/equivalent mutants are filtered/flagged. **AT-07** binary and family trained artifacts reproduce split metrics. **AT-08** ML-on/off localization ablation runs under identical candidate/test budgets. **AT-09** learned family model differs from simple detector rule labels and can abstain. **AT-10** untyped AST + call-site inference produces executable Hypothesis strategy without annotations. **AT-11** trials happen exclusively in sandbox. **AT-12** a reproduced crash on an unconfirmed domain is reported as observation, not confirmed contract violation. **AT-13** an in-contract implicit fault can drive repair without a preexisting expected return value, but only earns `VALIDATED_RUNTIME_FAULT_ONLY` until output semantics are independently checked. **AT-14** user confirms a **single** expected tuple; subsequent run uses A-tier, earlier run stays unchanged. **AT-15** LLM-guessed outputs remain C before confirmation. **AT-16** negative out-of-contract input cannot alone mark a high-severity bug. **AT-17** a trusted failing test highlights the actual covered fault path; absent traces never fabricate Ochiai. **AT-18** precedent lookup excludes held-out rows and displays genuine cosine similarities/edits. **AT-19** nearest-neighbor false friend does not bypass template preconditions or tests. **AT-20** low precedent similarity downgrades ML certainty but does not disable static/runtime checks. **AT-21** syntax-invalid and unsafe LLM patches are rejected before execution. **AT-22** bad patch fails regression, good patch fixes a witness and preserves existing tests. **AT-23** runtime measurement uses identical workloads, warmup/samples and distinguishes noise (`PERFORMANCE_INCONCLUSIVE`). **AT-24** smallest patch wins only after correctness gates. **AT-25** critical/high severity requires appropriate impact and evidence, not model probability. **AT-26** timeout, memory bomb and untrusted file accesses are contained by runner. **AT-27** report has all mandatory PS outputs with true null/unrun status. **AT-28** proof export includes model, split/index, source, tests, patch and runner hashes. **AT-29** demo fixture/results are plainly distinguished from blind external holdout. **AT-30** a spec-less unresolvable wrong-output case remains inconclusive rather than reported fixed.

# 15. Judge demonstration plan and challenging questions

### 15.1 Seven-minute scripted demo (adapt to slot length)

| Segment | Time | Visual proof |
|---|---:|---|
| Problem and promise | 0:00–0:40 | “Predict → Explain → Repair → Prove, or say unknown.” |
| Structural intelligence + trained model | 0:40–1:50 | Live AST/graph, **trained risk + family model**, real/mutation cohorts, localization ablation |
| Fault localization + witness | 1:50–3:00 | Suspicious line, **untyped input inference**, implicit crash or shrunk trusted wrong-output witness |
| Precedent + Repair Tournament | 3:00–4:45 | Real historical edits/similarity influence repair rank; candidate rejected, correct one passes; runtime and patch-size delta |
| Contract confirmation + evidence | 4:45–6:15 | **One-click output confirmation** creates A-tier rerun; Novelty Radar abstains on an unfamiliar sample; export provenance |
| Scope and close | 6:15–7:00 | One true held-out measurement, limits and exportable fix |

**Backup:** ship three pinned local fixtures and record source hashes: (A) algorithmic binary-search defect with reference oracle plus a **no-spec replay**, (B) no-hint runtime-fault case that asks for domain confirmation, (C) multi-function caller regression or novelty-abstain case. A fixture may seed an input program but must trigger **real** analysis/execution at demo time. Precomputed sample metrics must be clearly labeled.

### 15.2 Questions the panel will ask

**“How is this different from ChatGPT plus pytest?”** Independently trained binary/family models and code graphs predict/localize before tests; **historical real fixes actively rank repairs**; input inference plus A/B/I/C oracles produce evidence even when no tests exist; competing patches receive sandboxed, repeatable validation.

**“How do you show generalization rather than memorization?”** Project/bug-lineage/algorithm-problem splits, near-duplicate filtering, family-held-out tests and strictly external QuixBugs plus original blind cases. Report real-vs-synthetic domain shift and **localization hit-rate uplift with vs without the ML prior**. We cannot guarantee no foundation-LLM pretraining exposure to public benchmarks.

**“What if there is no correct expected output?”** Infer input candidates from call sites/AST and bounded sandbox trials; an **in-contract uncaught exception, assertion or reproducible timeout** can be an implicit oracle for operational failure. Wrong-result semantics still require a sound property/reference or **one-click confirmation of an exact expected output**. Otherwise `INCONCLUSIVE_NO_OUTPUT_ORACLE`.


**“What did the ML actually improve?”** Show frozen Top-1/Top-3/MRR localization with all rules/graphs/tests unchanged, first without ML then with binary and family priors. Separately show precedent retrieval improving repair@K or time-to-valid-patch; no score substitution for missing ablation data.

**“What does optimization mean?”** Correctness first; among validated patches, minimize changed AST/lines and dependency impact. Measure original/patch median and p95 runtime on comparable passing inputs with fixed runner and repeat counts; `PERFORMANCE_INCONCLUSIVE` when noisy.

**“Did you need to run BugsInPy to train?”** No. Both buggy and fixed snapshots plus diffs can be extracted statically. Execution is reserved for a small reproducible demo/audit subset; synthetic mutations get extra behavioral witness checks before high-confidence labels.

**“Could retrieval leak the answer to QuixBugs?”** Only train-split pairs are indexed, and QuixBugs is never supplied as retrieval, few-shot or threshold-tuning data. Public pretrained LLM exposure remains a disclosed caveat.

**“Can your sandbox run malicious code safely?”** Explain exact deployed runtime and restrictions; gVisor/microVM preferred. If the demo runs only in hardened Docker, explicitly restrict exposure and avoid a claim of fully secure multi-tenant sandboxing.

**“Does passing the tests mean the patch is correct?”** No. It means validated on a stated test set under a pinned environment; unknown edge cases and omitted dependencies remain acknowledged.

# 16. Risk register and fallback decisions

| Risk | Symptom | Mitigation / honest fallback |
|---|---|---|
| BugsInPy dependency/runtime reproduction | Historic project environments fail to build | **Train from source-only buggy/fixed diffs**, require no environment reproduction; separately execute just curated demo/audit cases |
| Dataset/retrieval leakage | Suspicious accuracy, precedent practically copies QuixBugs patch | Freeze project/algorithm group splits before mutation; index train pairs only, deduplicate, audit exemplar/LLM prompt exposure |
| Class imbalance | High accuracy with weak bug recall | PR-AUC, prevalence, stratification within group constraints, cost-aware threshold and calibration |
| Wrong inferred oracle or domain | Patch normalizes invalid inputs or invents expected output | A/B/I/C oracle ledger, **domain status**, one-click exact tuple confirmation, conservative inconclusive fallback |
| LLM overfitting to test cases | Visible tests pass, hidden tests fail | Holdouts not shown to repair model, independent generated tests, candidate tournament |
| Static graph unsoundness | Runtime calls missing | Mark unresolved edges and favor full-suite rerun; no graph-completeness claim |
| Unsafe user execution | Resource exhaustion or host interaction | Separate sandbox, strict resource/network restrictions, kill and audit; disable public runner if hardening unavailable |
| Time/compute limits | Embedding/LLM/model slow | TF-IDF + XGBoost primary path, cached artifacts, small per-job budgets, deterministic template fallback |
| Overbuilt UI, weak research | Beautiful dashboard but no trained model | Prioritize P0/P1 metrics and E2E before visual polish |
| Synthetic mutation shortcut | Classifier detects synthetic artifacts instead of bugs | Require killed mutants where possible, filter equivalent/stillborn cases, audit family balance and cross-domain error |
| Untyped strategy inference wrong | Sandbox crashes on nonsensical values | Rank by hints/call sites/AST; show domain-unconfirmed; bounded trials and human refinement |
| Historical precedent false friend | Similar function but incompatible fix | Apply template preconditions, context checks, full regressions and novelty abstention |
| Noisy runtime comparison | Tiny cases appear “10× faster” due to timer noise | Warmup, repeated runs, randomized paired order, variance and `PERFORMANCE_INCONCLUSIVE` |
| Overclaiming uniqueness | USP sounds like existing baseline | Present concrete mechanism, demonstrated differential value and an honest ablation |

# 17. Reference repository: useful patterns, not forced code reuse

The supplied reference, **Team-ASHTOJ/TATTVASTRA**, currently documents **JOCKY**, a typed forensic language/compiler and platform—not a ready-made Python defect-repair framework. Therefore Samyak should **not** import its compiler AST, LLVM toolchain, agent runtime or security model wholesale. Those are different language and deployment domains.

**Patterns worth borrowing:** a strict source-to-artifact provenance chain; versioned Pydantic/TypeScript contracts; separation of parsing/analysis from execution; explicit real-vs-fixture states; detailed requirement traceability; an evidence-first dashboard; stable source spans and failure states. Reimplement these *design practices* in the much smaller Samyak stack. The decision is based on the repository README and architecture/requirement-traceability documents inspected on 13 November 2026; it is not an assertion that these components are already compatible with Samyak.

# 18. Source and verification notes

The problem-statement requirements and 100-point rubric come from the supplied `Hackthon.docx`. The added corpus strategy and oracle safeguards are **Samyak design proposals**, not pre-existing benchmark claims. Relevant documentation below was checked or rechecked on 13 November 2026; pin the exact versions/commits before implementation. **Source-only BugsInPy extraction** and **generated mutations** must be documented with provenance, licensing and their own evaluation caveats.

1. **BugsInPy — real Python defects and reproductions.** https://github.com/soarsmu/BugsInPy
2. **QuixBugs — Python/Java program repair benchmark.** https://github.com/jkoppel/QuixBugs
3. **Hypothesis — property-based testing, shrinking and input generation.** https://hypothesis.readthedocs.io/en/latest/
4. **LibCST — format-preserving Python transforms and codemods.** https://libcst.readthedocs.io/en/latest/
5. **Microsoft CodeBERT / GraphCodeBERT — optional code representation extension.** https://github.com/microsoft/CodeBERT
6. **scikit-learn grouped cross-validation.** https://scikit-learn.org/stable/modules/cross_validation.html
7. **scikit-learn common pitfalls: avoiding leakage.** https://scikit-learn.org/stable/common_pitfalls.html
8. **coverage.py — Python line/branch coverage.** https://coverage.readthedocs.io/en/latest/
9. **Bandit — AST-based Python security checks.** https://bandit.readthedocs.io/en/latest/
10. **gVisor — stronger runtime isolation for untrusted applications.** https://github.com/google/gvisor
11. **TheAlgorithms/Python — algorithm seeds and open-source license:** https://github.com/TheAlgorithms/Python
12. **MBPP — seeded coding tasks, reference solutions and official task partitions:** https://github.com/google-research/google-research/blob/master/mbpp/README.md
13. **HumanEval — optional widely used short-code seed collection (contamination caveat):** https://github.com/openai/human-eval
14. **scikit-learn TF-IDF and cosine/nearest-neighbor APIs:** https://scikit-learn.org/stable/modules/feature_extraction.html ; https://scikit-learn.org/stable/modules/metrics.html#cosine-similarity
15. **Reference repository:** https://github.com/Team-ASHTOJ/TATTVASTRA ; see `README.md`, `docs/ARCHITECTURE.md` and `docs/REQUIREMENT_TRACEABILITY.md`.

---

## Final strategic verdict

**Samyak should win on evidence density, not feature count.** Its spine is **source-mined real repairs + verified algorithmic mutations + genuinely trained risk/family models + a real structural graph + input inference/implicit-oracle witnesses + precedent-grounded patch ranking + independently checked repairs + replayable evidence**. Ship that spine first. Present the **ten** USPs as design differentiators, but only call a USP delivered when its algorithm, visible UX and measured acceptance test exist. A system that can work usefully on unseen, untyped, test-less code *and* still say “this input domain/expected output is unconfirmed” is technically stronger than one that paints every LLM patch green.
