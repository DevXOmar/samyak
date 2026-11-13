"""Bounded public GitHub reads. Imported Python is parsed, never evaluated."""

import ast
import base64
import re
import time
from pathlib import PurePosixPath
import httpx
from fastapi import HTTPException
from pydantic import Field, field_validator
from .contracts import ContractModel
from .repair import SAFE_IMPORTS

URL = re.compile(r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?/?$")
CACHE = {}
EXCLUDED = {
    ".venv",
    "venv",
    "env",
    "site-packages",
    "__pycache__",
    "tests",
    "test",
    "migrations",
    "benchmarks",
    "vendor",
    "vendored",
    "third_party",
    "build",
    "dist",
    "generated",
    ".git",
}


class RepoRequest(ContractModel):
    url: str = Field(max_length=250)

    @field_validator("url")
    @classmethod
    def canonical(cls, value):
        m = URL.fullmatch(value)
        if not m or m[2] in {".", ".."}:
            raise ValueError(
                "Use https://github.com/OWNER/REPO without credentials, query, fragment or branch path"
            )
        return f"https://github.com/{m[1]}/{m[2]}"


class FileRequest(RepoRequest):
    sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    path: str = Field(min_length=1, max_length=500)

    @field_validator("path")
    @classmethod
    def safe_path(cls, value):
        if (
            "\\" in value
            or "%" in value
            or any(p in {"", "..", "."} for p in value.split("/"))
            or not value.endswith(".py")
            or value.startswith("/")
        ):
            raise ValueError("Select a regular recommended Python path")
        return value


class Recommended(ContractModel):
    path: str
    size: int
    blob_sha: str
    reason: str
    functions: int | None = None
    classes: int | None = None
    caveats: list[str] = Field(default_factory=list)


class RepoResult(ContractModel):
    repository: str
    url: str
    sha: str
    files: list[Recommended]
    partial: bool
    limits: str


class FileResult(ContractModel):
    repository: str
    sha: str
    path: str
    source: str
    functions: int
    classes: int
    caveats: list[str]


def fetch(path, cap=2_000_000):
    try:
        with httpx.Client(timeout=12, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "GET",
                "https://api.github.com" + path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "Samyak-public-source-inspector",
                },
            ) as response:
                if response.status_code != 200:
                    status = response.status_code
                    raise HTTPException(
                        429 if status in {403, 429} else 404 if status == 404 else 502,
                        "GitHub rate limit or access restriction; retry later"
                        if status in {403, 429}
                        else "Public repository/file unavailable"
                        if status == 404
                        else "GitHub request failed (redirects are refused)",
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > cap:
                        raise HTTPException(413, "GitHub response exceeded the bounded response limit")
                import json

                return json.loads(body)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "GitHub unavailable or invalid response; retry inspection") from exc


def eligible(row):
    path = row.get("path", "")
    return (
        row.get("type") == "blob"
        and row.get("mode") in {"100644", "100755"}
        and path.endswith(".py")
        and not any(p.lower() in EXCLUDED for p in PurePosixPath(path).parts)
        and not PurePosixPath(path).name.startswith(("test_", "bench_"))
        and not PurePosixPath(path).name.endswith(("_test.py", "_pb2.py"))
        and 0 < row.get("size", 0) <= 60000
    )


def content(repo, blob):
    data = fetch(f"/repos/{repo}/git/blobs/{blob}", 100_000)
    try:
        if data.get("encoding") != "base64" or data.get("size", 60001) > 60000:
            raise ValueError()
        source = base64.b64decode(data["content"], validate=False).decode("utf-8", errors="strict")
        if len(source) > 60000 or len(source.encode()) > 60000:
            raise ValueError()
        tree = ast.parse(source)
        if len(list(ast.walk(tree))) > 12000:
            raise ValueError()
    except (ValueError, KeyError, UnicodeError, SyntaxError, RecursionError) as exc:
        raise HTTPException(
            422, "Unsupported file: valid UTF-8 Python within 60,000 bytes/characters and AST budget required"
        ) from exc
    imports = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports.extend(a.name.split(".")[0] for a in n.names)
        if isinstance(n, ast.ImportFrom):
            imports.append((n.module or "").split(".")[0] if not n.level else "(sibling module)")
    missing = sorted(set(imports) - SAFE_IMPORTS - {"__future__"})
    caveats = (
        ["Additional dependencies required; standalone execution may be unsupported: " + ", ".join(missing)]
        if missing
        else []
    )
    return (
        source,
        sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree)),
        sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree)),
        caveats,
    )


def inspect(request):
    repo = request.url.removeprefix("https://github.com/")
    meta = fetch(f"/repos/{repo}")
    if meta.get("private"):
        raise HTTPException(404, "Only public repositories are supported")
    from urllib.parse import quote

    commit = fetch(f"/repos/{repo}/commits/{quote(meta['default_branch'], safe='')}")
    sha = commit.get("sha", "")
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise HTTPException(502, "GitHub returned an invalid commit identity")
    try:
        tree = fetch(f"/repos/{repo}/git/trees/{sha}?recursive=1")
    except HTTPException as exc:
        if exc.status_code != 413:
            raise
        tree = {"truncated": True}
    rows = tree.get("tree", [])
    partial = bool(tree.get("truncated"))
    if partial:
        rows = []
        queue = [("", sha)]
        seen = set()
        while queue and len(seen) < 8:
            prefix, ident = queue.pop(0)
            if ident in seen:
                continue
            seen.add(ident)
            sub = fetch(f"/repos/{repo}/git/trees/{ident}")
            for row in sub.get("tree", [])[:3000]:
                row = {**row, "path": prefix + row["path"]}
                if row["type"] == "tree" and not any(
                    p.lower() in EXCLUDED for p in PurePosixPath(row["path"]).parts
                ):
                    queue.append((row["path"] + "/", row["sha"]))
                else:
                    rows.append(row)
    candidates = sorted(
        (r for r in rows if eligible(r)),
        key=lambda r: (
            0
            if PurePosixPath(r["path"]).name in {"main.py", "app.py", "cli.py", "__main__.py"}
            else 1
            if r["path"].startswith("src/")
            else 2,
            r["size"],
            r["path"],
        ),
    )[:8]
    files = []
    texts = {}
    for row in candidates:
        item = Recommended(
            path=row["path"],
            size=row["size"],
            blob_sha=row["sha"],
            reason="Bounded Python source; contents not yet inspected",
        )
        try:
            text, functions, classes, caveats = content(repo, row["sha"])
            texts[item.path] = (text, functions, classes, caveats)
            item.functions, item.classes, item.caveats = functions, classes, caveats
            item.reason = (
                "Parsed Python with functions/classes and allowlisted imports"
                if not caveats and functions + classes
                else "Parsed Python; inspect dependency caveats"
                if caveats
                else "Parsed module statements; no function requirement"
            )
        except HTTPException as exc:
            if exc.status_code == 429:
                partial = True
                item.caveats = ["Content inspection paused by GitHub rate limit"]
            else:
                continue
        files.append(item)
    files.sort(
        key=lambda f: (
            bool(f.caveats),
            not bool(f.functions or f.classes),
            0 if PurePosixPath(f.path).name in {"main.py", "app.py", "cli.py", "__main__.py"} else 1,
            f.path,
        )
    )
    result = RepoResult(
        repository=repo,
        url=request.url,
        sha=sha,
        files=files,
        partial=partial,
        limits="At most 8 recommendations/content probes; 8 subtrees on truncated trees; 2 MB per tree; 60 KB per file. One selected file is the analysis unit.",
    )
    now = time.monotonic()
    for key in list(CACHE):
        if now - CACHE[key][0] > 600:
            CACHE.pop(key, None)
    if len(CACHE) >= 16:
        CACHE.pop(next(iter(CACHE)))
    CACHE[(request.url, sha)] = (now, result, texts)
    return result


def file(request):
    cached = CACHE.get((request.url, request.sha))
    if not cached or time.monotonic() - cached[0] > 600:
        raise HTTPException(409, "Inspect this repository again; pinned selection expired")
    item = next((f for f in cached[1].files if f.path == request.path), None)
    if not item:
        raise HTTPException(422, "Path was not a recommended regular Python blob at this SHA")
    value = cached[2].get(item.path) or content(cached[1].repository, item.blob_sha)
    return FileResult(
        repository=cached[1].repository,
        sha=request.sha,
        path=request.path,
        source=value[0],
        functions=value[1],
        classes=value[2],
        caveats=value[3],
    )
