from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
import json

VERSION = "1.2"
Domain = Literal["CONFIRMED", "UNCONFIRMED", "OUT_OF_CONTRACT"]
Tier = Literal["A", "B", "I", "C"]


class ContractModel(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True, extra="forbid")


class TestCase(ContractModel):
    mode: Literal["FUNCTION", "SCRIPT"] = "FUNCTION"
    stdin: str = Field(default="", max_length=8000)
    id: str = ""
    function: str = Field(pattern=r"^[A-Za-z_]\w*$", max_length=100)
    args: list[Any] = Field(default_factory=list, max_length=12)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    tier: Tier = "C"
    domain: Domain = "UNCONFIRMED"
    expected: Any = None
    has_expected: bool = False
    property: Literal["sorted_multiset"] | None = None
    origin: str = "GENERATED"
    reason: str = "Exploratory input; no output oracle"
    strategy: str | None = None
    minimized_from: str | None = None
    confirmation_id: str | None = None
    reviewer: str | None = None
    confirmed_at: str | None = None

    @model_validator(mode="after")
    def oracle_check(self):
        try:
            raw = json.dumps(
                {"args": self.args, "kwargs": self.kwargs, "expected": self.expected}, allow_nan=False
            )
        except (ValueError, TypeError) as exc:
            raise ValueError("Inputs and expectations must be finite JSON") from exc
        if len(raw.encode()) > 12000:
            raise ValueError("Per-case argument/output budget is 12 KB")
        if self.tier == "A" and not self.has_expected:
            raise ValueError("A oracle requires an exact expected output")
        if self.tier == "B" and self.property is None:
            raise ValueError("B oracle requires a supported, explicitly justified property")
        return self


class AnalysisRequest(ContractModel):
    mode: Literal["ANALYZE", "SCRIPT"] = "ANALYZE"
    stdin: str = Field(default="", max_length=8000)
    source: str = Field(min_length=1, max_length=60000)
    tests: list[TestCase] = Field(default_factory=list, max_length=64)
    fixture: Literal["binary_search", "average", "caller_regression", "unfamiliar"] | None = None
    property_contracts: dict[str, Literal["sorted_multiset"]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def bounded_suite(self):
        if len(self.model_dump_json().encode()) > 180000:
            raise ValueError("Submission and test suite budget is 180 KB")
        return self


class Confirmation(ContractModel):
    function: str = Field(pattern=r"^[A-Za-z_]\w*$")
    args: list[Any]
    kwargs: dict[str, Any] = Field(default_factory=dict)
    expected: Any = None
    reviewer: str = Field(min_length=1, max_length=100)


class DomainConfirmation(ContractModel):
    test_ids: list[str] = Field(min_length=1, max_length=64)
    reviewer: str = Field(min_length=1, max_length=100)


class PatchRequest(ContractModel):
    source: str = Field(min_length=1, max_length=60000)


class Span(ContractModel):
    start_line: int
    end_line: int
    start_col: int
    end_col: int


class Finding(ContractModel):
    id: str
    rule_id: str
    function: str
    span: Span
    explanation: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    evidence: str = "HYPOTHESIS"
    strength: float
    family: str
    qualification: str


class FunctionInfo(ContractModel):
    name: str
    span: Span
    source: str
    features: dict[str, float]
    risk: float | None = None
    family: str | None = None
    family_distribution: dict[str, float] = Field(default_factory=dict)


class Execution(ContractModel):
    test_id: str
    status: str
    output: Any = None
    error: str | None = None
    lines: list[int] = Field(default_factory=list)
    median_ms: float | None = None
    p95_ms: float | None = None
    samples_ms: list[float] = Field(default_factory=list)
    repeatable: bool | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: float | None = None
    traceback: str | None = None
    fault_lines: list[int] = Field(default_factory=list)


class Candidate(ContractModel):
    id: str
    source_hash: str
    source: str
    diff: str
    operator: str
    line: int
    prior: float
    context: dict[str, Any]
    changed_lines: int
    verdict: str = "UNVERIFIED_SUGGESTION"
    checks: list[dict[str, Any]] = Field(default_factory=list)
    results: list[Execution] = Field(default_factory=list)
    performance: dict[str, Any] = Field(default_factory=lambda: {"status": "PERFORMANCE_INCONCLUSIVE"})


class Report(ContractModel):
    contract_version: str = VERSION
    job_id: str
    parent_id: str | None = None
    source_hash: str
    source: str
    test_revision: str
    structure: dict[str, Any] = Field(default_factory=dict)
    functions: list[FunctionInfo] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    localization: list[dict[str, Any]] = Field(default_factory=list)
    inference: list[dict[str, Any]] = Field(default_factory=list)
    tests: list[TestCase] = Field(default_factory=list)
    original_results: list[Execution] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)
    precedents: list[dict[str, Any]] = Field(default_factory=list)
    model: dict[str, Any] = Field(default_factory=dict)
    runner: dict[str, Any] = Field(default_factory=dict)
    scanners: dict[str, Any] = Field(default_factory=dict)
    overall_risk: float | None = None
    severity: str | None = None
    verdict: str = "INCONCLUSIVE_NO_OUTPUT_ORACLE"
    limitations: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
    script_result: Execution | None = None
    intelligence: dict[str, Any] = Field(default_factory=dict)


class Job(ContractModel):
    contract_version: str = VERSION
    id: str
    parent_id: str | None
    status: str
    stage: str
    created_at: str
    updated_at: str
    error: str | None = None
    report_hash: str | None = None


class Event(ContractModel):
    id: int
    job_id: str
    stage: str
    message: str
    timestamp: str


class InvestigationRequest(ContractModel):
    action: Literal["replay", "witness", "precedents", "ledger", "twin", "metamorphic"]
    test_id: str | None = Field(default=None, max_length=100)


class ContractDecision(ContractModel):
    test_id: str
    expected: Any = None
    reviewer: str = Field(min_length=1, max_length=100)
    decision: Literal["REJECT_EXPECTATION"] = "REJECT_EXPECTATION"


class PropertyConfirmation(ContractModel):
    function: str = Field(pattern=r"^[A-Za-z_]\w*$", max_length=100)
    property: Literal["sorted_multiset"] = "sorted_multiset"
    reviewer: str = Field(min_length=1, max_length=100)


class Capabilities(ContractModel):
    contract_version: str = VERSION
    runner: dict[str, Any]
    worker: Literal["READY", "OFFLINE"]
    model_status: str
    model_id: str | None
    llm: Literal["CONFIGURED", "DISABLED_NO_CONFIGURATION"]
