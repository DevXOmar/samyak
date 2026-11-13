import base64
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from samyak.api import app
from samyak import github_import as gh

SHA = "a" * 40
BLOB = "b" * 40


@pytest.fixture
def client(monkeypatch):
    gh.CACHE.clear()

    def fetch(path, cap=0):
        if "/git/blobs/" in path:
            source = "def square(x):\n    return x * x\n"
            return {
                "encoding": "base64",
                "size": len(source),
                "content": base64.b64encode(source.encode()).decode(),
            }
        if "/git/trees/" in path:
            return {
                "tree": [
                    {"path": "src/square.py", "mode": "100644", "type": "blob", "size": 30, "sha": BLOB},
                    {"path": "tests/test_x.py", "mode": "100644", "type": "blob", "size": 30, "sha": BLOB},
                    {"path": "link.py", "mode": "120000", "type": "blob", "size": 30, "sha": BLOB},
                ],
                "truncated": False,
            }
        if "/commits/" in path:
            return {"sha": SHA}
        return {"private": False, "default_branch": "main"}

    monkeypatch.setattr(gh, "fetch", fetch)
    return TestClient(app)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://localhost/a/b",
        "https://github.com@127.0.0.1/a/b",
        "https://github.com/a/b?x=y",
        "https://github.com/a/b/tree/main",
        "https://github.com/a/../",
        "https://github.com/a/b#main",
    ],
)
def test_ssrf_rejection(client, url):
    assert client.post("/v1/github/inspect", json={"url": url}).status_code == 422


def test_pinned_regular_file_and_stale_path(client):
    result = client.post("/v1/github/inspect", json={"url": "https://github.com/a/b.git/"}).json()
    assert result["url"] == "https://github.com/a/b" and result["sha"] == SHA
    assert [r["path"] for r in result["files"]] == ["src/square.py"]
    request = {"url": result["url"], "sha": SHA, "path": "src/square.py"}
    assert client.post("/v1/github/file", json=request).json()["source"].startswith("def square")
    for path in ["../x.py", "/x.py", "link.py", "tests/test_x.py", "x%2f.py", "a\\b.py"]:
        assert client.post("/v1/github/file", json={**request, "path": path}).status_code == 422
    assert client.post("/v1/github/file", json={**request, "sha": "no"}).status_code == 422
    assert client.post("/v1/github/file", json={**request, "sha": "c" * 40}).status_code == 409


def test_empty_truncated_and_rank_dependencies(client, monkeypatch):
    original = gh.fetch

    def fetch(path, cap=0):
        if "/git/trees/" in path:
            if "?recursive" in path:
                return {"tree": [], "truncated": True}
            return {
                "tree": [
                    {"path": "main.py", "type": "blob", "mode": "100644", "size": 100, "sha": "c" * 40},
                    {"path": "pure.py", "type": "blob", "mode": "100644", "size": 100, "sha": BLOB},
                ]
            }
        if "/git/blobs/" in path and path.endswith("c" * 40):
            source = 'import requests\ndef main():\n    return requests.get("https://example.com")\n'
            return {
                "encoding": "base64",
                "size": len(source),
                "content": base64.b64encode(source.encode()).decode(),
            }
        return original(path, cap)

    monkeypatch.setattr(gh, "fetch", fetch)
    first = gh.inspect(gh.RepoRequest(url="https://github.com/a/b"))
    assert first.partial and first.files[0].path == "pure.py" and first.files[1].caveats
    assert first.model_dump() == gh.inspect(gh.RepoRequest(url="https://github.com/a/b")).model_dump()
    monkeypatch.setattr(
        gh, "fetch", lambda path, cap=0: {"tree": []} if "/git/trees/" in path else original(path, cap)
    )
    assert not gh.inspect(gh.RepoRequest(url="https://github.com/a/b")).files


def test_rate_limit_and_source_caps(client, monkeypatch):
    def unavailable(*args):
        raise HTTPException(429, "GitHub rate limit")

    monkeypatch.setattr(gh, "fetch", unavailable)
    assert client.post("/v1/github/inspect", json={"url": "https://github.com/a/b"}).status_code == 429
    for source in ["x" * 60001, "def :", "\ud800"]:
        raw = source.encode(errors="surrogatepass")
        monkeypatch.setattr(
            gh,
            "fetch",
            lambda *args: {"encoding": "base64", "size": len(raw), "content": base64.b64encode(raw).decode()},
        )
        with pytest.raises(HTTPException):
            gh.content("a/b", BLOB)


def test_fetch_host_caps_and_no_redirects(monkeypatch):
    import httpx

    original = httpx.Client
    calls = []

    def handle(request):
        calls.append(request)
        assert request.url.host == "api.github.com"
        assert "authorization" not in request.headers
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    monkeypatch.setattr(
        gh.httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handle))
    )
    with pytest.raises(HTTPException) as error:
        gh.fetch("/repos/a/b")
    assert error.value.status_code == 502 and len(calls) == 1
    monkeypatch.setattr(
        gh.httpx,
        "Client",
        lambda **kwargs: original(
            **kwargs, transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 100))
        ),
    )
    with pytest.raises(HTTPException) as error:
        gh.fetch("/repos/a/b", cap=10)
    assert error.value.status_code == 413
