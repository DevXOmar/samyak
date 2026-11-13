import asyncio
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from .contracts import (
    AnalysisRequest,
    Confirmation,
    DomainConfirmation,
    PatchRequest,
    Job,
    Report,
    Event,
    VERSION,
    TestCase,
    InvestigationRequest,
    ContractDecision,
    PropertyConfirmation,
)
from .fixtures import fixture
from .ledger import build_bundle
from .inference import identify
from .store import Store, digest

app = FastAPI(title="SAMYAK Evidence API", version=VERSION)


def store():
    return Store()


def get_job(ident):
    try:
        return store().job(ident)
    except KeyError:
        raise HTTPException(404, "Job not found")


def get_report(ident):
    get_job(ident)
    report = store().report(ident)
    if report is None:
        raise HTTPException(409, "Report is not ready")
    return report


@app.get("/health")
def health():
    return {"status": "ok", "contract_version": VERSION}


@app.get("/v1/fixtures/{name}", response_model=AnalysisRequest)
def get_fixture(name: str):
    if name not in {"binary_search", "average", "caller_regression", "unfamiliar"}:
        raise HTTPException(404, "Unknown source fixture")
    return fixture(name)


@app.post("/v1/analyses", response_model=Job, status_code=202)
def analyze(request: AnalysisRequest):
    # A fixture is provenance only. Never substitute source or precomputed results.
    return store().submit({"analysis": request.model_dump()})


@app.get("/v1/analyses/{ident}", response_model=Job)
def job(ident: str):
    return get_job(ident)


@app.get("/v1/analyses/{ident}/report", response_model=Report)
def report(ident: str):
    return get_report(ident)


@app.get(
    "/v1/analyses/{ident}/events",
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def events(ident: str, request: Request, after: int = 0):
    get_job(ident)
    try:
        cursor = max(after, int(request.headers.get("Last-Event-ID", "0")))
    except ValueError:
        raise HTTPException(422, "Invalid Last-Event-ID")

    async def stream():
        nonlocal cursor
        while not await request.is_disconnected():
            rows = store().events(ident, cursor)
            for row in rows:
                cursor = row["id"]
                yield f"id: {cursor}\nevent: stage\ndata: {json.dumps(row)}\n\n"
            if store().job(ident).status in {"COMPLETED", "FAILED"}:
                yield "event: done\ndata: {}\n\n"
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/v1/analyses/{ident}/tests", response_model=Job, status_code=202)
def generate_tests(ident: str):
    get_job(ident)
    payload = store().request(ident)
    payload.pop("investigation", None)
    payload.pop("base_report_hash", None)
    payload.pop("patch_source", None)
    return store().submit(payload, ident)


@app.post("/v1/analyses/{ident}/contracts/confirm", response_model=Job, status_code=202)
def confirm(ident: str, confirmation: Confirmation):
    previous = get_report(ident)
    payload = store().request(ident)
    test = identify(
        TestCase(
            function=confirmation.function,
            args=confirmation.args,
            kwargs=confirmation.kwargs,
            expected=confirmation.expected,
            has_expected=True,
            tier="A",
            domain="CONFIRMED",
            origin="USER_CONFIRMED",
            reviewer=confirmation.reviewer,
            confirmed_at=datetime.now(timezone.utc).isoformat(),
            confirmation_id=digest(confirmation.model_dump_json() + datetime.now(timezone.utc).isoformat()),
            reason=f"Exact input/output pair confirmed by {confirmation.reviewer}; no broader domain implied",
        )
    )
    if confirmation.function not in {f["name"] for f in previous["functions"]}:
        raise HTTPException(422, "Unknown function")
    tests = list(payload["analysis"]["tests"])
    # The new exact oracle supersedes an earlier expectation for the same tuple only in this new revision.
    tests = [
        t for t in tests if (t["function"], t["args"], t["kwargs"]) != (test.function, test.args, test.kwargs)
    ]
    payload["analysis"]["tests"] = [*tests, test.model_dump()]
    payload.pop("investigation", None)
    payload.pop("base_report_hash", None)
    payload.pop("patch_source", None)
    return store().submit(payload, ident)


@app.post("/v1/analyses/{ident}/contracts/domain", response_model=Job, status_code=202)
def confirm_domain(ident: str, confirmation: DomainConfirmation):
    previous = get_report(ident)
    known = {t["id"]: t for t in previous["tests"]}
    if any(i not in known for i in confirmation.test_ids):
        raise HTTPException(422, "Unknown test id")
    payload = store().request(ident)
    tests = list(payload["analysis"]["tests"])
    for i in confirmation.test_ids:
        t = TestCase.model_validate(known[i])
        t.domain = "CONFIRMED"
        if t.tier == "C":
            t.tier = "I"
        t.origin = "USER_DOMAIN_CONFIRMED"
        t.reviewer = confirmation.reviewer
        t.confirmed_at = datetime.now(timezone.utc).isoformat()
        t.reason = f"Exact input accepted by {confirmation.reviewer}; output semantics remain unknown"
        t.confirmation_id = digest(confirmation.model_dump_json() + datetime.now(timezone.utc).isoformat())
        tests.append(t.model_dump())
    payload["analysis"]["tests"] = tests
    payload.pop("investigation", None)
    payload.pop("base_report_hash", None)
    payload.pop("patch_source", None)
    return store().submit(payload, ident)


@app.post("/v1/analyses/{ident}/investigate", response_model=Job, status_code=202)
def investigate(ident: str, request: InvestigationRequest):
    previous = get_report(ident)
    known_ids = {t["id"] for t in previous["tests"]}
    witness_id = previous.get("intelligence", {}).get("witness", {}).get("test", {}).get("id")
    if witness_id:
        known_ids.add(witness_id)
    if request.test_id and request.test_id not in known_ids:
        raise HTTPException(422, "Unknown recorded test")
    payload = store().request(ident)
    payload["investigation"] = request.model_dump()
    payload["base_report_hash"] = store().job(ident).report_hash
    return store().submit(payload, ident)


@app.post("/v1/analyses/{ident}/contracts/decision", response_model=Job, status_code=202)
def decline_expectation(ident: str, decision: ContractDecision):
    previous = get_report(ident)
    if decision.test_id not in {t["id"] for t in previous["tests"]}:
        raise HTTPException(422, "Unknown recorded test")
    payload = store().request(ident)
    payload.pop("investigation", None)
    payload.pop("base_report_hash", None)
    payload.setdefault("decisions", []).append(
        {**decision.model_dump(), "timestamp": datetime.now(timezone.utc).isoformat()}
    )
    return store().submit(payload, ident)


@app.post("/v1/analyses/{ident}/contracts/property", response_model=Job, status_code=202)
def declare_property(ident: str, confirmation: PropertyConfirmation):
    previous = get_report(ident)
    if confirmation.function not in {f["name"] for f in previous["functions"]}:
        raise HTTPException(422, "Unknown function")
    payload = store().request(ident)
    payload.pop("investigation", None)
    payload.pop("base_report_hash", None)
    payload["analysis"]["property_contracts"][confirmation.function] = confirmation.property
    payload.setdefault("property_confirmations", []).append(
        {**confirmation.model_dump(), "timestamp": datetime.now(timezone.utc).isoformat()}
    )
    return store().submit(payload, ident)


@app.get("/v1/analyses/{ident}/patches")
def patches(ident: str):
    return get_report(ident)["candidates"]


@app.post("/v1/analyses/{ident}/patches/validate", response_model=Job, status_code=202)
def validate_patch(ident: str, patch: PatchRequest):
    get_report(ident)
    payload = store().request(ident)
    payload.pop("investigation", None)
    payload.pop("base_report_hash", None)
    payload["patch_source"] = patch.source
    return store().submit(payload, ident)


@app.get("/v1/analyses/{ident}/bundle")
def bundle(ident: str):
    report = get_report(ident)
    blob = build_bundle(report, store().request(ident), store().events(ident))
    return Response(
        blob,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="samyak-{ident}.zip"'},
    )


# Event schema participates in OpenAPI-generated TS contracts although SSE is a text transport.
app.openapi_schema = None
_original_openapi = app.openapi


def openapi_with_events():
    schema = _original_openapi()
    schema["components"]["schemas"]["Event"] = Event.model_json_schema()
    return schema


app.openapi = openapi_with_events
