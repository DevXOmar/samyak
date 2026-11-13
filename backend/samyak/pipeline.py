import json
from pathlib import Path
import subprocess
import tempfile
from .contracts import AnalysisRequest, Execution, Report
from .inference import infer, shrink_fault
from .ml import ModelService, novelty_evidence, index_identity, edit_priors
from .repair import OPERATORS, candidates, llm_candidates, make_candidate, safety, validate
from .runner import DockerRunner
from .store import digest
from .impact import enrich_tournament
from .ledger import ledger_metadata
from .structure import analyze, localize


def scanners(source):
    result = {}
    with tempfile.TemporaryDirectory(prefix="samyak-static-") as temp:
        path = Path(temp) / "submission.py"
        path.write_text(source)
        for name, command in [
            ("ruff", ["ruff", "check", "--output-format=json", str(path)]),
            ("bandit", ["bandit", "-f", "json", "-q", str(path)]),
        ]:
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=15)
                result[name] = {
                    "status": "SCANNED",
                    "exit_code": run.returncode,
                    "result": json.loads(run.stdout) if run.stdout else [],
                    "stderr": run.stderr[:1000],
                }
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                result[name] = {"status": "UNAVAILABLE", "reason": str(exc)}
    return result


def outputs(report):
    values = {
        "M1_CODE_INTELLIGENCE": report.structure or None,
        "M2_DEFECT_PREDICTION": {"highest_function_risk": report.overall_risk, "model": report.model}
        if report.overall_risk is not None
        else None,
        "M3_LOCALIZATION": report.localization or None,
        "M4_LOGICAL_ANALYSIS": [f.model_dump() for f in report.findings],
        "M5_REPAIRS": [c.id for c in report.candidates] or None,
        "M6_TESTS": len(report.tests) or None,
        "M7_VALIDATION": {
            "verdict": report.verdict,
            "candidate_verdicts": {c.id: c.verdict for c in report.candidates},
        },
        "M8_DASHBOARD": {"report_contract": report.contract_version, "job": report.job_id},
    }
    report.outputs = {
        key: {"status": "AVAILABLE" if value is not None else "UNAVAILABLE", "value": value}
        for key, value in values.items()
    }


def run_pipeline(ident, payload, stage, parent=None):
    request = AnalysisRequest.model_validate(payload["analysis"])
    source = request.source
    report = Report(
        job_id=ident, parent_id=parent, source_hash=digest(source), source=source, test_revision="PENDING"
    )
    stage("structure", "Parsing AST, tokens, scopes, CFG and lexical dependencies without execution")
    try:
        report.structure, report.functions, report.findings = analyze(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        report.verdict = "REJECTED_SYNTAX"
        report.limitations.append(str(exc))
        outputs(report)
        return report
    report.intelligence["actions"] = ["replay", "witness", "precedents", "ledger"]
    report.intelligence["contract_decisions"] = payload.get("decisions", [])
    report.intelligence["property_confirmations"] = payload.get("property_confirmations", [])
    report.scanners = scanners(source)
    stage(
        "prediction", "Loading independently trained binary and family models and train-only precedent index"
    )
    model = ModelService()
    model.predict(report.functions)
    report.model = dict(model.meta)
    report.precedents = model.retrieve(source)
    report.model["nearest_similarity"] = max((p["similarity"] for p in report.precedents), default=None)
    similarity = report.model["nearest_similarity"]
    report.model["novelty"] = (
        "INSUFFICIENT_EVIDENCE"
        if similarity is None
        else "HISTORICAL_PATTERN_UNFAMILIAR"
        if similarity < 0.15
        else "HISTORICAL_NEIGHBORS_AVAILABLE"
    )
    # Low similarity abstains on the family conclusion, never labels the source a bug.
    if similarity is not None and similarity < 0.15:
        for fn in report.functions:
            fn.family = "UNKNOWN_FAMILY"
    report.intelligence["novelty"] = novelty_evidence(model, report.functions, source, report.precedents)
    if report.intelligence["novelty"].get("abstain"):
        for fn in report.functions:
            fn.family = "UNKNOWN_FAMILY"
    report.intelligence["precedents"] = {
        "status": "AVAILABLE" if report.precedents else "NOT_SUPPORTED",
        "reason": "Train-only cosine neighbors influence applicable template priors; not output oracles",
        "index_id": index_identity(model.bundle) if model.bundle else None,
        "operator_distribution": edit_priors(report.precedents, OPERATORS),
        "comparison": {
            "status": "NOT_RUN",
            "reason": "Run the paired retrieval experiment to execute both candidate orders",
        },
    }
    report.overall_risk = max((f.risk for f in report.functions if f.risk is not None), default=None)
    stage(
        "inference",
        "Inferring inputs from annotations, literal call sites and AST operations; freezing test manifest",
    )
    report.inference, report.tests = infer(source, request.tests, request.property_contracts)
    report.test_revision = digest(json.dumps([t.model_dump() for t in report.tests], sort_keys=True))
    runner = DockerRunner()
    stage(
        "execution",
        "Executing original in restricted Docker containers, collecting outputs and line coverage",
    )
    blocked, reason = safety(source)
    if blocked:
        report.original_results = [
            Execution(test_id=t.id, status=blocked, error=reason) for t in report.tests
        ]
        report.verdict = blocked
    else:
        report.original_results = runner.run(source, report.tests)
        crash_indices = [i for i, r in enumerate(report.original_results) if r.status in {"ERROR", "TIMEOUT"}]
        if crash_indices:
            replays = runner.run(source, [report.tests[i] for i in crash_indices])
            for i, replay in zip(crash_indices, replays):
                original = report.original_results[i]
                original.repeatable = (original.status, original.error) == (replay.status, replay.error)
                if not original.repeatable:
                    original.status = "FLAKY"
        for inference in report.inference:
            related = [
                (t, r)
                for t, r in zip(report.tests, report.original_results)
                if t.function == inference["function"]
            ]
            inference["trials"] = [
                {
                    "test_id": t.id,
                    "status": "TYPE_REJECTED"
                    if r.error and r.error.startswith("TypeError")
                    else "ACCEPTED_EXECUTION"
                    if r.status == "PASS"
                    else "RUNTIME_FAULT"
                    if r.status == "ERROR"
                    else r.status,
                    "domain": t.domain,
                }
                for t, r in related
            ]
            inference["trial_status"] = "OBSERVED" if related else "NO_TRIALS"
        witness = shrink_fault(source, report.tests, report.original_results, runner)
        if witness:
            report.structure["minimal_witness"] = witness
    report.runner = runner.manifest
    stage("localization", "Fusing exposed model, rule, graph and eligible Ochiai signals")
    report.localization = localize(
        report.structure, report.functions, report.findings, report.tests, report.original_results
    )
    for finding in report.findings:
        confirmed = [
            (t, r)
            for t, r in zip(report.tests, report.original_results)
            if t.domain == "CONFIRMED"
            and t.tier in {"A", "B", "I"}
            and r.status in {"FAIL", "ERROR"}
            and t.function == finding.function
            and any(finding.span.start_line <= line <= finding.span.end_line for line in r.lines)
        ]
        observations = [
            r
            for t, r in zip(report.tests, report.original_results)
            if r.status == "ERROR" and t.function == finding.function
        ]
        if confirmed:
            finding.severity, finding.evidence = "HIGH", "FAULT_CONFIRMED"
            finding.qualification = "Confirmed failure on an explicit in-contract oracle; coverage associates this span, not proof of unique root cause"
        elif observations:
            finding.evidence = "RUNTIME_FAULT_DOMAIN_UNCONFIRMED"
    severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    report.severity = max(
        (f.severity for f in report.findings), key=lambda s: severity_order[s], default=None
    )
    stage("repair", "Creating immutable LibCST patch candidates with caller, witness and precedent context")
    generated, context = candidates(
        source, report.structure, report.findings, report.tests, report.original_results, report.precedents
    )
    llm, llm_status = llm_candidates(source, context, report.findings, report.tests, report.precedents)
    report.model["llm_status"] = llm_status
    report.intelligence["precedents"]["ranking"] = [
        {"candidate_id": c.id, "operator": c.operator, "prior": c.prior} for c in generated
    ]
    report.candidates = list({c.id: c for c in [*generated, *llm]}.values())[:8]
    if payload.get("patch_source"):
        custom = make_candidate(source, payload["patch_source"], "USER_CANDIDATE", 1, 0, context)
        report.candidates = [custom]
    stage(
        "validation",
        f"Validating {len(report.candidates)} candidates against the identical frozen suite and affected callers",
    )
    if not blocked:
        for candidate in report.candidates:
            validate(candidate, source, report.tests, report.original_results, runner)
        winners = [
            c
            for c in report.candidates
            if c.verdict in {"VALIDATED_ON_TESTS", "VALIDATED_RUNTIME_FAULT_ONLY"}
        ]
        if winners:
            winners.sort(key=lambda c: (c.verdict != "VALIDATED_ON_TESTS", c.changed_lines))
            report.verdict = winners[0].verdict
        elif any(r.status == "EXECUTION_UNAVAILABLE" for r in report.original_results):
            report.verdict = "EXECUTION_UNAVAILABLE"
        elif report.candidates:
            verdicts = [c.verdict for c in report.candidates]
            report.verdict = next(
                (
                    v
                    for v in [
                        "REJECTED_REGRESSION",
                        "FLAKY",
                        "INCONCLUSIVE_TIMEOUT",
                        "SANDBOX_ERROR",
                        "UNRESOLVED",
                    ]
                    if v in verdicts
                ),
                "INCONCLUSIVE_NO_OUTPUT_ORACLE",
            )
    enrich_tournament(report)
    report.intelligence["ledger"] = ledger_metadata(report)
    report.limitations += [
        "Docker-only isolation is development-grade; do not expose this runner as a public multi-tenant service",
        "Python 3.11 pure functions with finite JSON arguments/results; no package installation",
        "CFG, def-use and call resolution are bounded approximations; full available suites are rerun",
        "Generated type/domain guesses and unconfirmed crashes cannot certify a patch",
        "Performance is inconclusive unless equivalent workloads and a controlled sampling protocol support comparison",
    ]
    outputs(report)
    stage("evidence", "Hashing report, source, tests, candidate revisions and replay manifest")
    return report
