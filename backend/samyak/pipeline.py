import json
from pathlib import Path
import subprocess
import tempfile
from .contracts import AnalysisRequest, Execution, Finding, Report, Span
from .inference import infer, shrink_fault
from .ml import ModelService, novelty_evidence, index_identity, edit_priors
from .repair import OPERATORS, candidates, llm_candidates, make_candidate, safety, validate
from .runner import DockerRunner
from .store import digest
from .impact import enrich_tournament
from .ledger import ledger_metadata
from .twins import semantic_twin
from .atlas import syntax_tree
from .structure import analyze, localize
from .scripts import module_facts, execute_script


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
    report.intelligence["execution"] = {"mode": "FUNCTION_TESTS", "stdin": request.stdin}
    stage("structure", "Parsing AST, tokens, scopes, CFG and lexical dependencies without execution")
    try:
        report.structure, report.functions, report.findings = analyze(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        report.verdict = "REJECTED_SYNTAX"
        report.limitations.append("Python is the supported language. Submit valid Python source. " + str(exc))
        if isinstance(exc, SyntaxError) and exc.lineno:
            report.findings.append(
                Finding(
                    id="syntax",
                    rule_id="PYTHON_SYNTAX",
                    function="<module>",
                    span=Span(
                        start_line=exc.lineno,
                        end_line=exc.lineno,
                        start_col=max(0, (exc.offset or 1) - 1),
                        end_col=max(1, exc.offset or 1),
                    ),
                    explanation=report.limitations[-1],
                    strength=1.0,
                    family="OTHER",
                    evidence="SYNTAX_ERROR",
                    qualification="Python is the only supported language; no translation or compilation of other languages",
                )
            )
        outputs(report)
        return report
    module, module_findings = module_facts(source)
    report.structure["module"] = module
    report.structure["syntax_tree"] = syntax_tree(source)
    report.structure["graph"]["nodes"].extend(module["nodes"])
    report.structure["graph"]["edges"].extend(module["edges"])
    if any(c["target"] == "printf" for c in module["calls"]):
        report.limitations.append(
            "Python is the supported language. printf is a C library function, not a Python builtin; no C compilation or translation is performed."
        )
    report.findings.extend(module_findings)
    if request.mode == "SCRIPT" or module["statement_count"]:
        stage("execution", "Executing Python script as __main__ in restricted Docker")
        report.script_result, report.runner = execute_script(source, request.stdin)
        report.intelligence["execution"] = {
            "mode": "SCRIPT",
            "stdin": request.stdin,
            "domain": "UNCONFIRMED",
            "oracle": None,
        }
    if request.mode == "SCRIPT" or not report.functions:
        model = ModelService()
        if report.functions:
            stage("prediction", "Applying unchanged function models; module statements have no learned risk")
            model.predict(report.functions)
        report.model = dict(model.meta)
        report.overall_risk = max((f.risk for f in report.functions if f.risk is not None), default=None)
        report.model["applicability"] = "FUNCTIONS_ONLY" if report.functions else "NOT_APPLICABLE_SCRIPT_ONLY"
        if report.script_result is None:
            report.script_result, report.runner = execute_script(source, request.stdin)
        result = report.script_result
        report.verdict = result.status
        report.severity = "MEDIUM" if report.findings or result.fault_lines else None
        for line in dict.fromkeys(result.fault_lines):
            owner = next(
                (f.name for f in report.functions if f.span.start_line <= line <= f.span.end_line), "<module>"
            )
            source_line = source.splitlines()[line - 1] if line <= len(source.splitlines()) else ""
            report.findings.append(
                Finding(
                    id=f"script-runtime:{line}",
                    rule_id="RUNTIME_EXCEPTION",
                    function=owner,
                    span=Span(start_line=line, end_line=line, start_col=0, end_col=len(source_line.encode())),
                    explanation=result.error or result.status,
                    evidence="OBSERVED_RUNTIME_FAULT",
                    strength=1.0,
                    family="OTHER",
                    qualification="Observed for this exact stdin. Input domain is unconfirmed; no correctness claim.",
                )
            )
            report.localization.append(
                {
                    "line": line,
                    "function": "<module>",
                    "score": 1.0,
                    "signals": {"runtime_fault": True},
                    "mode": "OBSERVED_RUNTIME_FAULT",
                }
            )
        report.localization.extend(
            {
                "line": f.span.start_line,
                "function": "<module>",
                "score": f.strength,
                "signals": {"rule_strength": f.strength, "model_risk": None},
                "mode": "STATIC_HYPOTHESIS",
            }
            for f in module_findings
            if f.span.start_line not in result.fault_lines
        )
        stage(
            "localization",
            "Recording static hypotheses and exact observed traceback lines; no assumed input domain",
        )
        report.scanners = scanners(source)
        report.intelligence["execution"] = {
            "mode": "SCRIPT",
            "stdin": request.stdin,
            "domain": "UNCONFIRMED",
            "oracle": None,
            "qualification": "A successful process is not proof of correctness",
        }
        report.test_revision = digest(request.stdin)
        report.intelligence["ledger"] = ledger_metadata(report)
        report.limitations.append(
            "Script execution is an observation, not a correctness oracle or validated repair. Input domain remains unconfirmed."
        )
        outputs(report)
        report.outputs["M2_DEFECT_PREDICTION"]["status"] = (
            "AVAILABLE" if report.functions else "NOT_APPLICABLE"
        )
        report.outputs["M7_VALIDATION"] = {
            "status": "NOT_APPLICABLE",
            "value": {"execution": result.status, "reason": "Script observation has no output oracle"},
        }
        return report
    report.intelligence["actions"] = ["replay", "witness", "precedents", "ledger", "twin", "metamorphic"]
    report.intelligence["contract_decisions"] = payload.get("decisions", [])
    report.intelligence["property_confirmations"] = payload.get("property_confirmations", [])
    report.intelligence["metamorphic"] = {
        "status": "NOT_RUN" if request.property_contracts else "NOT_SUPPORTED",
        "reason": "Explicit sorting contract available; run transformed executions"
        if request.property_contracts
        else "Declare a sorting contract to enable justified metamorphic checks",
    }
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
    for decision in payload.get("decisions", []):
        for test in report.tests:
            same_tuple = (test.function, test.args, test.kwargs) == (
                decision.get("function"),
                decision.get("args"),
                decision.get("kwargs"),
            )
            same_expected = json.dumps(test.expected, sort_keys=True) == json.dumps(
                decision.get("expected"), sort_keys=True
            )
            later_confirmation = bool(test.confirmed_at and test.confirmed_at > decision.get("timestamp", ""))
            if (
                same_tuple
                and test.tier == "A"
                and test.has_expected
                and same_expected
                and not later_confirmation
            ):
                test.tier, test.has_expected, test.expected = "C", False, None
                test.origin = "RETRACTED_EXACT_EXPECTATION"
                test.reason = "This exact expected result was rejected in a later immutable contract revision; it cannot certify output behavior"
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
    report.intelligence["witness"] = {
        "status": "NOT_RUN",
        "reason": "Find the smallest supported, independently replayed failure. Exact semantic oracles are never transferred to new tuples.",
        "initial_runtime_observation": report.structure.get("minimal_witness"),
    }
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
            accepted_domain = any(
                t.domain == "CONFIRMED" and r.status == "ERROR" and t.function == finding.function
                for t, r in zip(report.tests, report.original_results)
            )
            finding.evidence = (
                "OBSERVED_RUNTIME_FAULT" if accepted_domain else "RUNTIME_FAULT_DOMAIN_UNCONFIRMED"
            )
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
    if (
        not blocked
        and not report.candidates
        and any(
            t.domain == "CONFIRMED" and t.tier in {"A", "B", "I"} and r.status in {"FAIL", "ERROR"}
            for t, r in zip(report.tests, report.original_results)
        )
    ):
        report.verdict = "UNRESOLVED"
    enrich_tournament(report)
    report.intelligence["ledger"] = ledger_metadata(report)
    eligibility = semantic_twin(source)
    report.intelligence["twin"] = (
        {
            "status": "NOT_RUN",
            "reason": "Run the full twin pipeline to measure stability",
            "eligibility": eligibility,
        }
        if eligibility["status"] == "ELIGIBLE"
        else eligibility
    )
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
