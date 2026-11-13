"""AST-identical CST parenthesization twins, with conservative eligibility checks."""

import ast
import libcst as cst
from .repair import safety
from .store import digest


def semantic_twin(source):
    rejected, reason = safety(source)
    if rejected:
        return {"status": "NOT_SUPPORTED", "reason": reason}
    tree = ast.parse(source)
    if any(
        isinstance(n, (ast.ClassDef, ast.AsyncFunctionDef, ast.Yield, ast.YieldFrom, ast.Await, ast.Lambda))
        for n in ast.walk(tree)
    ):
        return {
            "status": "NOT_SUPPORTED",
            "reason": "Classes, async, generators and lambdas are outside the bounded equivalence claim",
        }
    if any(isinstance(n, ast.FunctionDef) and n.decorator_list for n in ast.walk(tree)):
        return {"status": "NOT_SUPPORTED", "reason": "Decorated functions may inspect source or frames"}

    class Parenthesize(cst.CSTTransformer):
        changed = False

        def leave_BinaryOperation(self, original, updated):
            self.changed = True
            return updated.with_changes(
                lpar=(cst.LeftParen(), *updated.lpar), rpar=(*updated.rpar, cst.RightParen())
            )

        def leave_Return(self, original, updated):
            if updated.value is not None and not self.changed:
                self.changed = True
                return updated.with_changes(
                    value=updated.value.with_changes(
                        lpar=(cst.LeftParen(), *updated.value.lpar),
                        rpar=(*updated.value.rpar, cst.RightParen()),
                    )
                )
            return updated

    transform = Parenthesize()
    twin = cst.parse_module(source).visit(transform).code
    if twin == source or ast.dump(ast.parse(twin), include_attributes=False) != ast.dump(
        tree, include_attributes=False
    ):
        return {
            "status": "NOT_SUPPORTED",
            "reason": "No AST-identical parenthesization transform is available",
        }
    return {
        "status": "ELIGIBLE",
        "source": twin,
        "source_hash": digest(twin),
        "ast_hash": digest(ast.dump(tree, include_attributes=False)),
        "transform": "LibCST redundant parentheses; AST identical without source attributes",
        "reason": "Bounded syntactic equivalence under the source/reflection allowlist; not general program equivalence",
    }


def challenge_twin(report, payload, runner, stage):
    twin = semantic_twin(report.source)
    if twin["status"] != "ELIGIBLE":
        report.intelligence["twin"] = twin
        return
    from .pipeline import run_pipeline

    analysis = dict(payload["analysis"])
    analysis["source"] = twin["source"]
    analysis["fixture"] = None
    stage("twin", "Running the complete analysis and repair pipeline on an AST-identical source twin")
    compared = run_pipeline(
        report.job_id, {"analysis": analysis}, lambda s, m: stage("twin_" + s, m), report.parent_id
    )
    original_lines = [r["line"] for r in report.localization[:3]]
    twin_lines = [r["line"] for r in compared.localization[:3]]
    report.intelligence["twin"] = {
        **twin,
        "status": "MEASURED",
        "original_risk": report.overall_risk,
        "twin_risk": compared.overall_risk,
        "risk_delta": compared.overall_risk - report.overall_risk
        if compared.overall_risk is not None and report.overall_risk is not None
        else None,
        "original_top3": original_lines,
        "twin_top3": twin_lines,
        "top3_overlap": len(set(original_lines) & set(twin_lines)),
        "original_verdict": report.verdict,
        "twin_verdict": compared.verdict,
        "repair_verdicts": [c.verdict for c in compared.candidates],
        "execution_results": [r.model_dump() for r in compared.original_results],
        "candidate_evidence": [c.model_dump() for c in compared.candidates],
        "model_id": compared.model.get("model_id"),
        "runner_digest": compared.runner.get("digest"),
        "comparison_scope": "This source and syntactic twin only",
    }
