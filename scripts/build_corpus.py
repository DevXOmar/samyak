import ast
from collections import Counter
import difflib
import json
from pathlib import Path
from samyak.contracts import TestCase
from samyak.mutations import mutations
from samyak.runner import DockerRunner
from samyak.store import digest
from samyak.ml import code_text
from scripts.data_sources import partition

ROOT = Path(__file__).resolve().parents[1]


def normalized_hash(source):
    class Normalize(ast.NodeTransformer):
        def visit_Name(self, node):
            return ast.copy_location(ast.Name(id="v", ctx=node.ctx), node)

        def visit_arg(self, node):
            node.arg = "v"
            return node

        def visit_FunctionDef(self, node):
            node.name = "f"
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body = node.body[1:]
            return self.generic_visit(node)

    return digest(ast.dump(Normalize().visit(ast.parse(source))))


def main():
    manifest = json.loads((ROOT / "data/source_manifest.json").read_text())
    runner = DockerRunner()
    counts = Counter()
    pairs, seen = [], set()
    if not runner.available():
        counts["execution_unavailable_mutants_excluded"] += 1
    else:
        for seed in manifest["seeds"]:
            # Verify frozen split was assigned before mutation generation.
            assert seed["split"] == partition("algorithm:" + seed["id"])
            fixed = (ROOT / seed["path"]).read_text()
            assert digest(fixed) == seed["extracted_hash"], "Seed artifact hash mismatch"
            tests = [
                TestCase(id=str(i), function=seed["function"], args=a) for i, a in enumerate(seed["inputs"])
            ]
            originals = runner.run(fixed, tests)
            counts["seed_executions"] += len(originals)
            for index, mutant in enumerate(mutations(fixed, seed["function"])):
                counts["mutants_generated"] += 1
                results = runner.run(mutant["buggy"], tests)
                witnesses = []
                for test, a, b in zip(tests, originals, results):
                    if a.status == "PASS" and (
                        b.status == "ERROR"
                        or b.status == "PASS"
                        and (type(a.output) is not type(b.output) or a.output != b.output)
                    ):
                        witnesses.append(
                            {"args": test.args, "original": a.model_dump(), "mutant": b.model_dump()}
                        )
                if not witnesses:
                    counts["unkilled_or_unresolved_excluded"] += 1
                    continue
                fn_bug = next(
                    n
                    for n in ast.parse(mutant["buggy"]).body
                    if isinstance(n, ast.FunctionDef) and n.name == seed["function"]
                )
                fn_fix = next(
                    n
                    for n in ast.parse(mutant["fixed"]).body
                    if isinstance(n, ast.FunctionDef) and n.name == seed["function"]
                )
                pair = {
                    **mutant,
                    "buggy": ast.get_source_segment(mutant["buggy"], fn_bug),
                    "fixed": ast.get_source_segment(mutant["fixed"], fn_fix),
                    "fault_lines": [
                        line - fn_bug.lineno + 1
                        for line in mutant["fault_lines"]
                        if fn_bug.lineno <= line <= fn_bug.end_lineno
                    ],
                    "id": f"algorithm/{seed['id']}/{seed['function']}/{index}",
                    "group": "algorithm:" + seed["id"],
                    "split": seed["split"],
                    "domain": "SYNTHETIC_ALGORITHM",
                    "confidence": "SANDBOX_DISTINGUISHING_WITNESS",
                    "witnesses": witnesses[:1],
                    "origin": seed["origin"],
                    "license_path": "data/seeds/THEALGORITHMS_LICENSE.md",
                }
                pairs.append(pair)
                counts["witnessed_mutants"] += 1
            print(seed["id"], dict(counts), flush=True)
    pairs += manifest["pairs"]
    # Group-level near-duplicate ancestors cannot cross partitions. Exact row duplicates are removed below.
    group_signatures, filtered = {}, []
    for pair in pairs:
        try:
            signature = normalized_hash(pair["fixed"])
            old_group = group_signatures.get(signature)
            if old_group and old_group != pair["group"]:
                counts["near_duplicate_lineage_excluded"] += 1
                continue
            group_signatures[signature] = pair["group"]
            exact = (digest(code_text(pair["buggy"])), digest(code_text(pair["fixed"])))
            if exact in seen:
                counts["duplicate_pairs_excluded"] += 1
                continue
            seen.add(exact)
            pair["diff"] = "".join(
                difflib.unified_diff(
                    pair["buggy"].splitlines(True),
                    pair["fixed"].splitlines(True),
                    fromfile="buggy.py",
                    tofile="fixed.py",
                )
            )
            filtered.append(pair)
        except (SyntaxError, ValueError):
            counts["unparsable_pair_excluded"] += 1
    # Historical bug lineages across revisions can share a function; move conflicting hashes out of all splits.
    partitions_by_hash = {}
    for pair in filtered:
        for key in ("buggy", "fixed"):
            partitions_by_hash.setdefault(digest(code_text(pair[key])), set()).add(pair["split"])
    filtered = [
        p
        for p in filtered
        if all(len(partitions_by_hash[digest(code_text(p[k]))]) == 1 for k in ("buggy", "fixed"))
    ]
    output = {
        "schema": "1.0",
        "seed": 20261113,
        "runner": runner.manifest,
        "quality": dict(counts),
        "pairs": filtered,
        "sources_manifest_hash": digest((ROOT / "data/source_manifest.json").read_bytes()),
    }
    (ROOT / "data/corpus.json").write_text(json.dumps(output, indent=2))
    print("Retained", len(filtered), "pairs", dict(Counter(p["split"] for p in filtered)))


if __name__ == "__main__":
    main()
