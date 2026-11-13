"""Source-only acquisition. No project installs, imports, or submitted-code execution."""

import ast
import json
from pathlib import Path
import subprocess
import urllib.request
import hashlib
import difflib
from samyak.edits import normalized_edit

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = "30507bbe41397065728167fb09aa820f9fce8dc7"
BUGSINPY = "11c5f1eea954a42132cfd06bf257766a7963e0fd"
SEEDS = [
    ("maths/abs.py", "abs_val", [[-5.1], [0], [5]]),
    ("maths/abs.py", "abs_min", [[[0, 5, 1]], [[3, -10, -2]], [[1]], [[]]]),
    ("maths/abs.py", "abs_max_sort", [[[0, 5, 1]], [[3, -10, -2]], [[1]], [[]]]),
    ("maths/average_median.py", "median", [[[0]], [[4, 1, 3, 2]], [[2, 7, 6]], [[]]]),
    ("maths/average_mode.py", "mode", [[[]], [[1]], [[1, 1, 2]], [[1, 2]]]),
    ("maths/average_mean.py", "mean", [[[1, 2, 3]], [[0]], [[-2, 2]], [[]]]),
    ("maths/ceil.py", "ceil", [[-1.1], [0], [1.1], [1.0]]),
    ("maths/factorial.py", "factorial", [[0], [1], [3], [5], [-1]]),
    ("maths/is_square_free.py", "is_square_free", [[[2, 3]], [[2, 2]], [[]]]),
    ("maths/sum_of_digits.py", "sum_of_digits", [[0], [1], [123], [-12]]),
    ("maths/signum.py", "signum", [[-3], [0], [2]]),
    ("maths/perfect_number.py", "perfect", [[1], [6], [28], [12]]),
    ("maths/double_factorial.py", "double_factorial_iterative", [[0], [1], [4], [5], [-1]]),
    ("maths/aliquot_sum.py", "aliquot_sum", [[1], [6], [12], [0]]),
    ("maths/is_int_palindrome.py", "is_int_palindrome", [[0], [121], [123], [-121]]),
    ("searches/linear_search.py", "linear_search", [[[], 1], [[1], 1], [[1, 2, 3], 3], [[1, 2], 4]]),
    ("strings/is_isogram.py", "is_isogram", [[""], ["abc"], ["aba"], ["AbA"]]),
    ("maths/power_using_recursion.py", "power", [[2, 0], [2, 3], [3, 2], [2, -2]]),
    ("maths/factors.py", "factors_of_a_number", [[1], [6], [12], [13]]),
    ("maths/number_of_digits.py", "num_digits", [[0], [9], [123], [-22]]),
    ("maths/automorphic_number.py", "is_automorphic_number", [[0], [1], [5], [6], [7], [25]]),
    ("maths/persistence.py", "multiplicative_persistence", [[0], [7], [39], [999]]),
    ("maths/triangular_numbers.py", "is_triangular", [[0], [1], [3], [4], [6]]),
    ("maths/hexagonal_number.py", "hexagonal", [[1], [2], [3], [5]]),
]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def partition(group):
    value = int(sha("samyak-v1:" + group)[:8], 16) % 10
    return "test" if value < 2 else "validation" if value == 2 else "calibration" if value == 3 else "train"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "SAMYAK-source-only-research"})
    return urllib.request.urlopen(request, timeout=30).read().decode()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main():
    dest = ROOT / "data/seeds"
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "1.0",
        "sources": [],
        "exclusions": [],
        "pairs": [],
        "seeds": [],
        "policy": "Split by project/problem before mutations; never install historical dependencies; QuixBugs excluded",
    }
    repo = ROOT / "data/upstream/algorithms"
    if not repo.exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "https://github.com/TheAlgorithms/Python.git", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "fetch", "origin", ALGORITHMS], check=True)
    license_text = git(repo, "show", f"{ALGORITHMS}:LICENSE.md")
    (dest / "THEALGORITHMS_LICENSE.md").write_text(license_text + "\n")
    manifest["sources"].append(
        {
            "name": "TheAlgorithms/Python",
            "revision": ALGORITHMS,
            "license": "MIT",
            "license_sha256": sha(license_text),
        }
    )
    for path, function, inputs in SEEDS:
        try:
            raw = git(repo, "show", f"{ALGORITHMS}:{path}")
            tree = ast.parse(raw)
            funcs = [
                f
                for f in tree.body
                if isinstance(f, ast.FunctionDef) and not f.name.startswith(("test_", "benchmark"))
            ]
            target = next(f for f in funcs if f.name == function)
            # Literal source extraction; no imports are executed. All function dependencies retained.
            module = (
                "from __future__ import annotations\nimport math\n"
                + "\n\n".join(ast.get_source_segment(raw, f) for f in funcs)
                + "\n"
            )
            ident = path.replace("/", "__")
            (dest / ident).write_text(module)
            manifest["seeds"].append(
                {
                    "id": path,
                    "path": f"data/seeds/{ident}",
                    "function": function,
                    "source_hash": sha(raw),
                    "extracted_hash": sha(module),
                    "split": partition("algorithm:" + path),
                    "inputs": inputs,
                    "origin": f"https://github.com/TheAlgorithms/Python/blob/{ALGORITHMS}/{path}",
                    "license": "MIT",
                    "target_source": ast.get_source_segment(raw, target),
                }
            )
        except (SyntaxError, StopIteration, subprocess.CalledProcessError) as exc:
            manifest["exclusions"].append(
                {"source": path, "reason": str(exc) or "Function absent at pinned revision"}
            )
    bugs = ROOT / "data/upstream/bugsinpy"
    if not bugs.exists():
        subprocess.run(["git", "clone", "https://github.com/soarsmu/BugsInPy.git", str(bugs)], check=True)
    subprocess.run(["git", "-C", str(bugs), "fetch", "origin", BUGSINPY], check=True)
    manifest["sources"].append(
        {
            "name": "BugsInPy",
            "revision": BUGSINPY,
            "usage": "metadata only; per-project source license retained",
        }
    )
    # Whole projects are reserved before accessing code or labels.
    projects = {
        "black": "train",
        "cookiecutter": "train",
        "PySnooper": "train",
        "httpie": "validation",
        "tornado": "calibration",
        "luigi": "test",
    }
    for project, split in projects.items():
        for bug in [1, 2]:
            try:

                def metadata(path):
                    text = git(bugs, "show", f"{BUGSINPY}:{path}")
                    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)

                project_info = metadata(f"projects/{project}/project.info")
                info = metadata(f"projects/{project}/bugs/{bug}/bug.info")
                url = project_info["github_url"].strip('"')
                owner_repo = url.removeprefix("https://github.com/").removesuffix(".git")
                before, after = info["buggy_commit_id"].strip('"'), info["fixed_commit_id"].strip('"')
                compare = json.loads(
                    fetch(f"https://api.github.com/repos/{owner_repo}/compare/{before}...{after}")
                )
                licenses = None
                for license_path in ["LICENSE", "LICENSE.md", "LICENSE.rst", "LICENSE.txt"]:
                    try:
                        licenses = fetch(
                            f"https://raw.githubusercontent.com/{owner_repo}/{after}/{license_path}"
                        )
                        break
                    except Exception:
                        pass
                if not licenses:
                    raise ValueError("No source license retrieved; excluded")
                (dest / f"{project}_LICENSE").write_text(licenses)
                for item in compare["files"]:
                    path = item["filename"]
                    if not path.endswith(".py") or "test" in path.lower() or item["status"] != "modified":
                        continue
                    old = fetch(
                        f"https://raw.githubusercontent.com/{owner_repo}/{before}/{item.get('previous_filename', path)}"
                    )
                    new = fetch(f"https://raw.githubusercontent.com/{owner_repo}/{after}/{path}")
                    try:
                        old_funcs = {
                            f.name: f for f in ast.walk(ast.parse(old)) if isinstance(f, ast.FunctionDef)
                        }
                        new_funcs = {
                            f.name: f for f in ast.walk(ast.parse(new)) if isinstance(f, ast.FunctionDef)
                        }
                    except SyntaxError:
                        continue
                    for name in sorted(old_funcs.keys() & new_funcs.keys()):
                        a, b = (
                            ast.get_source_segment(old, old_funcs[name]),
                            ast.get_source_segment(new, new_funcs[name]),
                        )
                        import textwrap

                        a, b = textwrap.dedent(a), textwrap.dedent(b)
                        if a == b or max(len(a), len(b)) > 12000:
                            continue
                        fault_lines = []
                        for tag, i, j, _, _ in difflib.SequenceMatcher(
                            None, a.splitlines(), b.splitlines()
                        ).get_opcodes():
                            if tag != "equal":
                                fault_lines.extend(range(i + 1, max(i + 2, j + 1)))
                        manifest["pairs"].append(
                            {
                                "id": f"{project}/{bug}/{path}/{name}",
                                "group": f"project:{project}",
                                "split": split,
                                "buggy": a,
                                "fixed": b,
                                "family": "OTHER",
                                "fault_lines": fault_lines,
                                "operator": normalized_edit(a, b),
                                "domain": "REAL_BUGSINPY",
                                "confidence": "REPORTED_BUG_FIX_SOURCE_ONLY",
                                "buggy_revision": before,
                                "fixed_revision": after,
                                "origin": url,
                                "path": path,
                                "license_path": f"data/seeds/{project}_LICENSE",
                            }
                        )
            except Exception as exc:
                manifest["exclusions"].append({"source": f"BugsInPy/{project}/{bug}", "reason": str(exc)})
    (ROOT / "data/source_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {
                "seeds": len(manifest["seeds"]),
                "historical_pairs": len(manifest["pairs"]),
                "exclusions": manifest["exclusions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
