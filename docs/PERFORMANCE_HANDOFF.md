# Measured analysis and Model Lab changes

All changes remain local. No training, dependencies, execution-result cache, API removal or runner-image change was introduced.

## Measurements

`scripts/profile_analysis.py` instruments the real Store/worker/pipeline and Docker adapter. It saves content-hashed reports and SQLite event timestamps under ignored `var/performance/<label>/`. `docs/PERFORMANCE_RESULTS.json` preserves the measured comparison, identities, stage intervals, counters and verdicts. These are engineering measurements, never served as fresh demo results.

| Fixture | Before | Two candidate suites | Reduction | Docker run invocations before/after | Test executions requested before/after |
|---|---:|---:|---:|---:|---:|
| Binary search | 8.139s | 6.204s | 23.8% | 7 / 7 | 79 / 79 |
| Caller regression | 14.886s | 9.186s | 38.3% | 10 / 10 | 164 / 164 |
| Ledger reconciler | 39.690s | 22.839s | 42.5% | 15 / 15 | 474 / 474 |

Single local runs, same fixture requests, source hashes, test revisions, model ID and runner digest. All original and patched status/output/error observations, candidate checks, candidate IDs/verdicts and script stdout/stderr/fault/coverage evidence were compared and matched. Runtime samples naturally differ; no optimization/correctness claim is made from those noisy per-case samples. This is a local wall-time measurement, not a statistically established universal speedup.

The initial validation stage dominated: 6.03s / 11.34s / 33.46s. After limiting concurrency to two it measured 4.08s / 5.65s / 16.51s. Setup-only optimization remained approximately flat (8.34 / 14.94 / 40.77s sequential), so the measured benefit comes primarily from bounded independent validation concurrency. Image inspections fell from 7/10/15 to 1/1/2. Ledger still performs its genuine module/main execution; it is not a docstring-only program.

The three baseline fixtures' eager witness search reached already-bounded cases, so deferral did not reduce their Docker/test counts. General costly minimization is now exclusively the existing explicit witness investigation. Initial failures and required original/candidate replays remain intact. Removing validation runs to inflate a benchmark would weaken the evidence; none were skipped.

## Implementation and reproducibility

- `SAMYAK_CANDIDATE_CONCURRENCY=2` is the measured default, maximum two. Set `1` for constrained hosts. Candidate result ordering remains unchanged. Every suite runs in its own ephemeral container; each test still gets a separate restricted subprocess. Container CPU/RAM/PID/network/read-only/no-secrets restrictions are unchanged. All security/applicability, trusted regression and replay gates remain.
- A runner instance resolves and pins its digest once. New jobs resolve tags again, invalidating changed images rather than retaining stale process-wide availability. A missing Docker executable still fails closed; actual Docker failures never become passes.
- Model reuse is process-local and bounded to the latest artifact identity. Every construction rechecks the manifest and artifact SHA-256; deserialization uses those exact verified bytes. Directory/CURRENT, manifest or artifact changes invalidate the cache. Per-instance metadata is copied; no submitted execution result is cached.
- Worker monotonic stage durations, total processing wall time and actual Docker/observation counters are persisted in `report.intelligence.timing`. The unchanged SSE event timestamps power active-stage, elapsed-clock and completed-stage duration UI. Queue time and store finalization are distinguished from processing time.
- Model Lab uses actual held-out PR-AUC/ROC-AUC/F1/n, separate cohort selection, RF/XGB comparison bars, measured ablation values and family count heatmaps. Function risks/static findings and unknown-family/novelty diagnostics remain distinct from held-out reliability. Tiny cohorts/no localization uplift remain explicit. Existing bundle, history, novelty, ledger and twin actions remain available.

Repeat current measurements with `PYTHONPATH=backend:. .venv/bin/python scripts/profile_analysis.py new-run`. To compare sequentially set `SAMYAK_CANDIDATE_CONCURRENCY=1`; compare identity/verdict fields before interpreting wall times. The recorded `before` run was collected before source changes, not reconstructed or reused as execution output.

Remaining bottleneck: full candidate suites and mandatory fresh-case replays. Model hash verification and scanner time are retained deliberately. Two containers may be slower on a constrained/contended host; the explicit sequential switch is available. Docker-unavailable cases cannot provide runtime speed measurements and remain fail-closed.

Live-progress recovery: if the event stream delivers no stage event for 15 seconds while a job is active, the client reads the existing job/timeline endpoints at most once per 15-second silence window. It merges real events by persisted ID and finishes from the actual completed report. Normal SSE remains primary; completed/restored jobs do not poll and recovery never resubmits source. This addresses an observed proxy stall where a 19-second completed twin job remained displayed RUNNING.

Verification observed: targeted Docker/parser/model-cache/fixture/investigation checks passed (24 tests), followed by `make check` (87 collected backend tests, 11 frontend tests, lint/typecheck and production build). A fourth dedicated deferral test added during that run also passed with the cache/timing tests. Metrics/cohort/missing-data/reload browser checks passed (4 workflows); live novelty and witness/retrieval/twin/ledger actions passed on settled code. A deliberately stalled SSE test passed using persisted-state recovery without resubmitting. Desktop/mobile light/dark screenshots were inspected. Earlier browser attempts during live source editing hit a Monaco hot-reload disposed-instance error; settled reruns passed. No fabricated timings or inference uplift are claimed.
