"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Braces,
  Check,
  CircleDot,
  Command,
  Download,
  FileCode2,
  FlaskConical,
  GitBranch,
  Layers3,
  Maximize2,
  Minimize2,
  Moon,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Sun,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/hooks/use-theme";
import { executionReadyToRerun } from "@/lib/readiness";
import { useCapabilities } from "@/hooks/use-capabilities";
import { useAnalysis } from "@/hooks/use-analysis";
import {
  observed,
  observationLabel,
  observationTone,
  riskLabel,
  tone,
  type Report,
  type TestCase,
  type AnalysisRequest,
} from "@/lib/client";
const ModelMetrics = dynamic(() => import("@/components/model-metrics"));
const Experiment = dynamic(() => import("@/components/intelligence-panel"));
const CodeEditor = dynamic(() => import("@/components/code-editor"), {
  ssr: false,
});
const Atlas = dynamic(() => import("@/components/fault-atlas"), { ssr: false });
const PatchDiff = dynamic(() => import("@/components/patch-diff"), {
  ssr: false,
});
const NAV = [
  "Workbench",
  "Fault Atlas",
  "Contract Studio",
  "Repair Arena",
  "Model Lab & Vault",
] as const;
type Workspace = (typeof NAV)[number];
const STAGES = [
  ["structure", "Parsing"],
  ["prediction", "Predicting"],
  ["localization", "Localizing"],
  ["inference", "Generating tests"],
  ["execution", "Executing"],
  ["repair", "Repairing"],
  ["validation", "Validating"],
];
const EMPTY: Report["findings"] = [];
function Json({ value }: { value: unknown }) {
  return <pre className="compact-json">{JSON.stringify(value, null, 2)}</pre>;
}
function Empty({
  title = "Your next investigation starts here",
  copy = "Paste a Python function, load a source fixture, or upload a .py file. Analyze to build a live evidence trail.",
}: {
  title?: string;
  copy?: string;
}) {
  return (
    <div className="panel empty">
      <Braces size={25} strokeWidth={1.3} />
      <h2>{title}</h2>
      <p>{copy}</p>
    </div>
  );
}

export default function Workbench() {
  const a = useAnalysis();
  const capabilities = useCapabilities();
  const report = a.visibleReport;
  const [workspace, setWorkspace] = useState<Workspace>("Workbench");
  const [theme, setTheme] = useTheme();
  const [line, setLine] = useState<number | null>(null);
  const [revealToken, setRevealToken] = useState(0);
  const [cursorLine, setCursorLine] = useState<number | null>(null);
  const [selected, setSelected] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [tab, setTab] = useState("source");
  const [testDraft, setTestDraft] = useState("");
  const [dialog, setDialog] = useState<
    "tests" | "confirmation" | "candidate" | null
  >(null);
  const [confirmId, setConfirmId] = useState("");
  const [expected, setExpected] = useState("");
  const [customPatch, setCustomPatch] = useState("");
  const upload = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLElement>(null);
  const editorTop = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDialog(null);
        setFullscreen(false);
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  useEffect(() => {
    if (!dialog) return;
    const previous = document.activeElement as HTMLElement | null;
    const root = modalRef.current;
    const focusable = () =>
      root
        ? Array.from(
            root.querySelectorAll<HTMLElement>(
              "button:not(:disabled),input,textarea,select,a[href]",
            ),
          )
        : [];
    focusable()
      .find((e) => e.tagName === "INPUT" || e.tagName === "TEXTAREA")
      ?.focus();
    function trap(event: KeyboardEvent) {
      if (event.key !== "Tab") return;
      const items = focusable();
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [dialog]);
  const chooseLine = useCallback((at: number) => {
    setLine(at);
    setCursorLine(at);
  }, []);
  const chooseFinding = (at: number) => {
    setRevealToken((v) => v + 1);
    setLine(at);
    setCursorLine(at);
    setWorkspace("Workbench");
    editorTop.current?.scrollIntoView({
      block: "nearest",
      behavior: "instant",
    });
  };
  const edit = (value: string) => {
    a.setSource(value);
    setLine(null);
  };
  const selectedIndex = report?.candidates[selected] ? selected : 0;
  const candidate = report?.candidates[selected] || report?.candidates[0];
  const finding =
    report?.findings.find((f) => f.span.start_line === (cursorLine || line)) ||
    report?.findings[0];
  const ranked = report?.localization.find(
    (r) => r.line === (cursorLine || line || finding?.span.start_line),
  );
  const originals = new Map(
    report?.original_results.map((r) => [r.test_id, r]),
  );
  const patched = new Map(candidate?.results.map((r) => [r.test_id, r]));
  const confirmation = report?.tests.find((t) => t.id === confirmId);
  const details = report?.intelligence || {};
  const can = (action: string) =>
    Array.isArray(details.actions) && details.actions.includes(action);
  const investigate = (action: string, extra: object = {}) =>
    report &&
    void a.run(`/v1/analyses/${report.job_id}/investigate`, {
      action,
      ...extra,
    });
  const modal = (type: typeof dialog) => {
    if (type === "tests") setTestDraft(JSON.stringify(a.tests, null, 2));
    if (type === "candidate") setCustomPatch(candidate?.source || a.source);
    setDialog(type);
  };
  async function load(name: NonNullable<AnalysisRequest["fixture"]>) {
    setLine(null);
    setSelected(0);
    setWorkspace("Workbench");
    await a.load(name);
  }
  function confirm(id: string) {
    const test = report?.tests.find((t) => t.id === id);
    if (!test) return;
    setConfirmId(id);
    setExpected(test.has_expected ? JSON.stringify(test.expected) : "");
    setDialog("confirmation");
  }
  function candidateProposal(id: string) {
    if (!report) return null;
    const proposed = report.candidates
      .flatMap((c) => c.results)
      .find((r) => r.test_id === id && r.status === "PASS");
    if (!proposed) return null;
    const declined =
      Array.isArray(report.intelligence.contract_decisions) &&
      (
        report.intelligence.contract_decisions as {
          test_id: string;
          expected: unknown;
        }[]
      ).some(
        (d) =>
          d.test_id === id &&
          JSON.stringify(d.expected) === JSON.stringify(proposed.output),
      );
    return declined ? null : proposed;
  }
  function acceptProposal(id: string, output: unknown) {
    const t = report?.tests.find((t) => t.id === id);
    if (report && t)
      void a.run(`/v1/analyses/${report.job_id}/contracts/confirm`, {
        function: t.function,
        args: t.args,
        kwargs: t.kwargs,
        expected: output,
        reviewer: "workbench-user",
      });
  }
  function caseLabel(id: unknown) {
    const test = report?.tests.find((t) => t.id === id);
    return test
      ? `${test.function}(${JSON.stringify(test.args)})`
      : String(id || "Gate");
  }
  function submitConfirmation() {
    if (!report || !confirmation) return;
    try {
      const value: unknown = JSON.parse(expected);
      setDialog(null);
      void a.run(`/v1/analyses/${report.job_id}/contracts/confirm`, {
        function: confirmation.function,
        args: confirmation.args,
        kwargs: confirmation.kwargs,
        expected: value,
        reviewer: "workbench-user",
      });
    } catch (e) {
      a.setError(`Enter a valid JSON expected output. ${String(e)}`);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Layers3 size={17} strokeWidth={1.4} />
          </div>
          <span className="brand-name">SAMYAK</span>
          <span className="brand-caption">CODE INTELLIGENCE / YUKTIK</span>
        </div>
        <div className="top-actions">
          <span className="label desktop-only">Python 3.11</span>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!report}
            onClick={() =>
              report &&
              downloadBundle(`/api/v1/analyses/${report.job_id}/bundle`)
            }
          >
            <Download size={13} />
            <span className="desktop-only">Export evidence</span>
          </Button>
        </div>
      </header>
      <nav
        className="workspace-nav"
        aria-label="Investigation workspaces"
        role="tablist"
      >
        {NAV.map((name, index) => (
          <button
            key={name}
            role="tab"
            aria-selected={workspace === name}
            aria-controls="workspace-content"
            onClick={() => setWorkspace(name)}
          >
            <span className="nav-index">0{index + 1}</span>
            {name}
          </button>
        ))}
      </nav>
      <main className="workspace-main" id="workspace-content" role="tabpanel">
        <div className="page-intro">
          <div>
            <div className="label gold">Evidence, before certainty.</div>
            <h1>
              {workspace === "Workbench"
                ? "A clearer view of what could break."
                : workspace === "Fault Atlas"
                  ? "Follow the fault through the code."
                  : workspace === "Contract Studio"
                    ? "Turn observations into testable intent."
                    : workspace === "Repair Arena"
                      ? "Let the evidence choose the repair."
                      : "Every claim, with a chain of evidence."}
            </h1>
            <p className="intro-copy">
              {workspace === "Workbench"
                ? "Inspect structure. Discover counterexamples. Validate a minimal repair."
                : "One investigation. Immutable revisions. Inspectable computation."}
            </p>
          </div>
          <div className="intro-action flex-row">
            <Badge tone={tone(a.job?.status)}>
              {a.job?.status || "READY TO INVESTIGATE"}
            </Badge>
            {a.job ? (
              <span className="hash">{a.job.id.slice(0, 8)}</span>
            ) : (
              <span className="label">PHASE 02</span>
            )}
          </div>
        </div>
        <div
          className="flex-row mb-3 text-[10px] muted"
          aria-label="Live service health"
          role="status"
        >
          Live services ·{" "}
          {capabilities.offline
            ? "API offline"
            : capabilities.status
              ? `Runner ${capabilities.status.runner.status} · Worker ${capabilities.status.worker} · Model ${capabilities.status.model_status}`
              : "Checking…"}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void capabilities.check()}
          >
            Recheck
          </Button>
        </div>
        {report && report.functions.length === 0 ? (
          <div className="notice">
            No analyzable Python functions. Define a Python function to obtain
            function risk, generated inputs and repair evidence. Module-level
            statements such as print calls have no function risk score.
          </div>
        ) : null}
        {executionReadyToRerun(
          report?.runner.status,
          capabilities.status?.runner.status,
          capabilities.offline,
        ) &&
        report &&
        report.functions.length > 0 ? (
          <div className="notice">
            <strong>Execution is ready — rerun analysis</strong>
            <p>
              This immutable report records an earlier unavailable runner. Live
              readiness does not change its historical results.
            </p>
            <Button
              disabled={a.busy}
              onClick={() =>
                void a.run(`/v1/analyses/${report.job_id}/tests`, {})
              }
            >
              Rerun analysis
            </Button>
          </div>
        ) : null}
        {capabilities.offline ? (
          <div className="notice error" role="status">
            API is offline. Start the local services, then retry.
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void capabilities.check()}
            >
              Check connection
            </Button>
          </div>
        ) : capabilities.status &&
          (capabilities.status.worker === "OFFLINE" ||
            capabilities.status.runner.status !== "AVAILABLE") ? (
          <div className="notice" role="status">
            {capabilities.status.worker === "OFFLINE"
              ? "Background worker is offline; submissions remain queued. "
              : ""}
            {capabilities.status.runner.status !== "AVAILABLE"
              ? "Docker execution is unavailable. Static analysis remains usable; execution fails closed. "
              : ""}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void capabilities.check()}
            >
              Recheck availability
            </Button>
          </div>
        ) : null}
        {a.error ? (
          <div className="notice error" role="alert">
            <div className="flex-row">
              <span>{a.error}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  void capabilities.check();
                  void a.retry();
                }}
              >
                Retry connection
              </Button>
            </div>
          </div>
        ) : null}
        {a.connection === "reconnecting" ? (
          <div className="notice" role="status">
            Connection interrupted. Reconnecting to persisted events; the worker
            continues independently.
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                void capabilities.check();
                void a.retry();
              }}
            >
              Reconnect now
            </Button>
          </div>
        ) : null}
        {a.stale ? (
          <div className="notice" role="status">
            Source changed. Findings, markers and verdicts are invalidated for
            this buffer.
            <Button size="sm" variant="ghost" onClick={() => a.restore()}>
              Restore analyzed snapshot
            </Button>
          </div>
        ) : null}
        {workspace === "Workbench" ? (
          <>
            <div
              className="demo-launcher"
              aria-label="Guided live demonstrations"
            >
              {(
                [
                  [
                    "binary_search",
                    "Boundary, not a guess",
                    "Reference oracle → minimal patch",
                    GitBranch,
                  ],
                  [
                    "average",
                    "An unknown contract",
                    "No hints → runtime witness → confirm",
                    FlaskConical,
                  ],
                  [
                    "caller_regression",
                    "The caller trap",
                    "A tempting fix, a real regression",
                    ShieldCheck,
                  ],
                ] as const
              ).map(([name, title, copy, Icon]) => (
                <button
                  className="panel demo-card"
                  disabled={a.busy}
                  key={name}
                  onClick={() => void load(name)}
                >
                  <Icon className="demo-icon" size={17} strokeWidth={1.5} />
                  <div>
                    <strong>{title}</strong>
                    <span>{copy}</span>
                  </div>
                  <ArrowUpRight size={12} className="muted ml-auto shrink-0" />
                </button>
              ))}
              <button
                className="panel demo-card"
                disabled={a.busy}
                onClick={() => void load("unfamiliar")}
              >
                <Sparkles size={17} className="demo-icon" />
                <div>
                  <strong>Correct, but suspicious</strong>
                  <span>Novelty signals → restraint → abstention</span>
                </div>
                <ArrowUpRight size={12} className="muted ml-auto shrink-0" />
              </button>
            </div>
            <div className="panel workflow" aria-live="polite">
              {STAGES.map(([stage, label]) => {
                const done = a.events.some((e) => e.stage === stage);
                const active = a.busy && a.job?.stage === stage;
                return (
                  <span className="workflow-step" key={stage}>
                    <i
                      className={`stage-dot ${active ? "stage-active" : done ? "stage-done" : ""}`}
                    />
                    {label}
                    {active ? <span className="gold">· live</span> : null}
                  </span>
                );
              })}
            </div>
            <div className="workspace-split" ref={editorTop}>
              <section
                className={`panel editor-shell ${fullscreen ? "editor-fullscreen" : ""}`}
              >
                <div className="editor-tabs">
                  <div className="file-tabs">
                    <button
                      className={`file-tab ${tab !== "source" ? "inactive" : ""}`}
                      onClick={() => setTab("source")}
                    >
                      <FileCode2 size={13} className="gold" />
                      {a.fixture ? `${a.fixture}.py` : "submission.py"}
                      {a.stale ? <CircleDot size={8} /> : null}
                    </button>
                    <button
                      className={`file-tab ${tab !== "tests" ? "inactive" : ""}`}
                      onClick={() => {
                        setTab("tests");
                        modal("tests");
                      }}
                    >
                      <Braces size={12} />
                      tests.json <span className="muted">{a.tests.length}</span>
                    </button>
                  </div>
                  <div className="flex-row">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Upload Python file"
                      disabled={a.busy}
                      onClick={() => upload.current?.click()}
                    >
                      <Upload size={14} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={
                        fullscreen
                          ? "Exit fullscreen editor"
                          : "Fullscreen editor"
                      }
                      onClick={() => setFullscreen(!fullscreen)}
                    >
                      {fullscreen ? (
                        <Minimize2 size={14} />
                      ) : (
                        <Maximize2 size={14} />
                      )}
                    </Button>
                  </div>
                </div>
                <div className="editor-body">
                  <CodeEditor
                    revealToken={revealToken}
                    height="100%"
                    value={a.source}
                    onChange={edit}
                    findings={report?.findings || EMPTY}
                    line={line}
                    theme={theme}
                    onAnalyze={() => !a.busy && a.source.trim() && void a.run()}
                    onSelect={setCursorLine}
                  />
                </div>
                <div className="editor-footer">
                  <span>
                    {a.source.split("\n").length} lines{" "}
                    <span className="mx-2">·</span>
                    {new TextEncoder().encode(a.source).length} bytes{" "}
                    <span className="desktop-only ml-3">UTF-8 / Python</span>
                  </span>
                  <div className="flex-row">
                    <span className="desktop-only muted flex-row">
                      <Command size={11} />↵
                    </span>
                    <Button
                      size="sm"
                      disabled={a.busy || !a.source.trim()}
                      onClick={() => {
                        setSelected(0);
                        void a.run();
                      }}
                    >
                      <Play size={12} fill="currentColor" />
                      {a.busy ? "Investigating…" : "Analyze source"}
                    </Button>
                  </div>
                </div>
              </section>
              <aside className="evidence-rail">
                <section className="panel rail-section">
                  <div className="flex-row justify-between">
                    <span className="label">Evidence rail</span>
                    <span className="gold">
                      <CircleDot size={12} />
                    </span>
                  </div>
                  {finding ? (
                    <>
                      <div className="flex-row mt-4">
                        <Badge
                          tone={finding.severity === "HIGH" ? "bad" : "warn"}
                        >
                          {finding.severity}
                        </Badge>
                        <code className="text-[10px] muted">
                          {finding.function}:{finding.span.start_line}
                        </code>
                      </div>
                      <h3 className="finding-title">
                        {finding.rule_id.replaceAll("_", " ").toLowerCase()}
                      </h3>
                      <p className="finding-copy">{finding.explanation}</p>
                      <div className="mt-3">
                        <Badge>{finding.evidence}</Badge>
                      </div>
                      <p className="text-[10px] muted mt-3">
                        {finding.qualification}
                      </p>
                      {ranked
                        ? Object.entries(
                            ranked.signals as Record<string, number | null>,
                          ).map(([key, value]) => (
                            <div className="signal-row" key={key}>
                              <span>{key.replaceAll("_", " ")}</span>
                              <div className="signal-bar">
                                <i
                                  style={{ width: `${(value || 0) * 100}%` }}
                                />
                              </div>
                              <code>
                                {value == null ? "—" : value.toFixed(2)}
                              </code>
                            </div>
                          ))
                        : null}
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-5 w-full"
                        onClick={() => setWorkspace("Contract Studio")}
                      >
                        Inspect inputs & witnesses
                        <ArrowRight size={12} />
                      </Button>
                    </>
                  ) : (
                    <>
                      <h3 className="mt-5 mb-2">
                        Select a question. Follow its evidence.
                      </h3>
                      <p className="finding-copy">
                        Findings and graph nodes reveal source, model, rule and
                        execution contributions here.
                      </p>
                      <div className="metric-inline mt-4">
                        <span className="muted">Modeled function risk</span>
                        <strong>{riskLabel(report?.overall_risk)}</strong>
                      </div>
                      <div className="metric-inline">
                        <span className="muted">Severity</span>
                        <strong>{report?.severity || "Not assessed"}</strong>
                      </div>
                    </>
                  )}
                </section>
                <section className="panel rail-section">
                  <div className="flex-row justify-between">
                    <span className="label">Current decision</span>
                    <ShieldCheck size={13} className="muted" />
                  </div>
                  <div className="mt-4" data-testid="verdict">
                    <Badge tone={tone(report?.verdict)}>
                      {report?.verdict ||
                        (a.busy ? "COMPUTING EVIDENCE" : "AWAITING ANALYSIS")}
                    </Badge>
                  </div>
                  <p className="text-[10px] muted mt-3">
                    A learned risk is a prediction. Passing recorded tests
                    supports only the tested behavior.
                  </p>
                  {report?.runner.status === "EXECUTION_UNAVAILABLE" &&
                  report.functions.length > 0 ? (
                    <div className="notice mt-3">
                      Historical job: execution was unavailable. See live
                      service health for current readiness.
                    </div>
                  ) : null}
                  <span className="label text-[8px]">
                    Docker isolation / development-grade
                  </span>
                </section>
              </aside>
            </div>
            <div className="bottom-evidence">
              <section className="panel">
                <div className="panel-heading">
                  <h2>Lines worth investigating</h2>
                  <span className="label">
                    {report?.findings.length || 0} findings
                  </span>
                </div>
                <div className="panel-body">
                  {report?.findings.length ? (
                    <div className="finding-list">
                      {report.findings.map((f) => (
                        <button
                          key={f.id}
                          className={`panel finding ${finding?.id === f.id ? "selected" : ""}`}
                          onClick={() => chooseFinding(f.span.start_line)}
                        >
                          <div className="flex-row justify-between">
                            <code className="text-[10px] gold">
                              L{f.span.start_line} · {f.function}
                            </code>
                            <Badge
                              tone={f.severity === "HIGH" ? "bad" : "warn"}
                            >
                              {f.severity}
                            </Badge>
                          </div>
                          <h3 className="finding-title">
                            {f.rule_id.replaceAll("_", " ").toLowerCase()}
                          </h3>
                          <p className="finding-copy">{f.explanation}</p>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title={
                        report
                          ? "No supported rule finding"
                          : "Evidence will appear here"
                      }
                      copy={
                        report
                          ? "No supported rule fired. This does not prove the code is defect free."
                          : "Run an analysis to connect each prediction to a source span and an observable check."
                      }
                    />
                  )}
                </div>
              </section>
              <section className="panel">
                <div className="panel-heading">
                  <h2>Computation journal</h2>
                  <Badge>
                    {a.connection === "live"
                      ? "LIVE / SSE"
                      : a.events.length
                        ? "PERSISTED"
                        : "NOT STARTED"}
                  </Badge>
                </div>
                <div className="panel-body">
                  <Timeline events={a.events} />
                  {!a.events.length ? (
                    <p className="muted text-xs">
                      Actual worker events and timestamps. No simulated
                      progress.
                    </p>
                  ) : null}
                </div>
              </section>
            </div>
          </>
        ) : !report ? (
          <Empty
            title={
              a.busy
                ? "The worker is investigating"
                : a.stale
                  ? "This buffer needs a new investigation"
                  : "An investigation connects these workspaces"
            }
            copy={
              a.busy
                ? "Persisted computation continues. Return to Workbench to follow its live stages."
                : "Analyze source in Workbench to inspect this evidence."
            }
          />
        ) : (
          <>
            {workspace === "Fault Atlas" ? (
              <>
                <div className="workspace-split">
                  <Atlas
                    report={report}
                    onSelect={chooseLine}
                    line={line}
                    dark={theme === "dark"}
                  />
                  <section className="panel rail-section">
                    <div className="flex-row justify-between">
                      <span className="label">Source inspection</span>
                      <code className="text-[9px] gold">L{line || 1}</code>
                    </div>
                    <div className="source-peek mt-3">
                      <CodeEditor
                        value={report.source}
                        onChange={() => {}}
                        findings={report.findings}
                        line={line}
                        theme={theme}
                        height="100%"
                        readOnly
                        modelPath="atlas-inspection.py"
                        onSelect={chooseLine}
                      />
                    </div>
                    <p className="label mt-5">Ranked source spans</p>
                    {report.localization.slice(0, 6).map((r, i) => (
                      <button
                        key={`${r.function}-${r.line}`}
                        className="metric-inline w-full text-left"
                        onClick={() => chooseFinding(Number(r.line))}
                      >
                        <span>
                          <span className="muted mr-2">{i + 1}.</span>
                          <code>
                            {String(r.function)}:{String(r.line)}
                          </code>
                        </span>
                        <code className="gold">
                          {Number(r.score).toFixed(3)}
                        </code>
                      </button>
                    ))}
                  </section>
                </div>
                <div className="bottom-evidence">
                  <section className="panel panel-body">
                    <h2 className="mb-4">Learned function estimates</h2>
                    {report.functions.map((f) => (
                      <div
                        className="metric-inline"
                        key={`${f.name}-${f.span.start_line}`}
                      >
                        <button
                          onClick={() => chooseFinding(f.span.start_line)}
                        >
                          <code>{f.name}</code>
                        </button>
                        <div className="flex-row">
                          <Badge>{f.family || "UNKNOWN"}</Badge>
                          <span className="gold mono">{riskLabel(f.risk)}</span>
                        </div>
                      </div>
                    ))}
                  </section>
                  <section className="panel panel-body">
                    <h2 className="mb-4">Selected contributions</h2>
                    <Json value={ranked || report.localization[0]} />
                  </section>
                </div>
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Blast radius"
                  data={details.blast_radius}
                  busy={a.busy}
                  run={investigate}
                />
              </>
            ) : null}
            {workspace === "Contract Studio" ? (
              <>
                <div className="page-intro">
                  <div>
                    <h2>Counterexample & Contract Studio</h2>
                    <p className="intro-copy">
                      A · exact expected behavior / B · justified property / I ·
                      operational fault / C · exploratory
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={a.busy}
                    onClick={() =>
                      void a.run(`/v1/analyses/${report.job_id}/tests`, {})
                    }
                  >
                    <FlaskConical size={13} />
                    Generate a new revision
                  </Button>
                </div>
                <section className="panel panel-body mb-5">
                  <div className="flex-row justify-between">
                    <div>
                      <h3>A property needs an explicit contract.</h3>
                      <p className="intro-copy">
                        Declare one function as an ascending sort of a finite
                        integer list, preserving every multiplicity. Only then
                        can the Shield justify B-tier relations.
                      </p>
                    </div>
                    <div className="flex-row">
                      {report.functions
                        .filter((f) => f.features.parameters === 1)
                        .map((f) => (
                          <Button
                            key={f.name}
                            variant="outline"
                            size="sm"
                            disabled={a.busy}
                            onClick={() =>
                              void a.run(
                                `/v1/analyses/${report.job_id}/contracts/property`,
                                {
                                  function: f.name,
                                  property: "sorted_multiset",
                                  reviewer: "workbench-user",
                                },
                              )
                            }
                          >
                            Declare sorting contract: {f.name}
                          </Button>
                        ))}
                    </div>
                  </div>
                </section>
                <div className="data-grid mb-5">
                  {report.inference.map((entry, i) => (
                    <section className="panel panel-body" key={i}>
                      <span className="label">Inferred signature</span>
                      <h3 className="mono mt-3">{String(entry.function)}</h3>
                      <Json value={entry.parameters || entry.unsupported} />
                    </section>
                  ))}
                </div>
                <div className="panel table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Input / source</th>
                        <th>Oracle / domain</th>
                        <th>Observation</th>
                        <th>Expected</th>
                        <th>Next action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.tests.map((t) => {
                        const r = originals.get(t.id);
                        const proposal = !t.has_expected
                          ? candidateProposal(t.id)
                          : null;
                        return (
                          <tr key={t.id}>
                            <td>
                              <code>
                                {t.function}({JSON.stringify(t.args)})
                              </code>
                              <p className="muted text-[10px] max-w-64 mt-2">
                                {t.reason}
                              </p>
                            </td>
                            <td>
                              <Badge>{t.tier}</Badge>
                              <p className="text-[9px] muted mt-2">
                                {t.domain}
                              </p>
                            </td>
                            <td>
                              <Badge tone={observationTone(t, r)}>
                                {observationLabel(t, r)}
                              </Badge>
                              <p className="mono text-[10px] mt-2 max-w-56 break-all">
                                {observed(r)}
                              </p>
                            </td>
                            <td>
                              <code>
                                {t.has_expected
                                  ? JSON.stringify(t.expected)
                                  : t.property || "No output oracle"}
                              </code>
                            </td>
                            <td>
                              <div className="flex flex-col gap-2 items-start">
                                {proposal ? (
                                  <>
                                    <span className="text-[9px] muted">
                                      Candidate proposes{" "}
                                      {JSON.stringify(proposal.output)} ·
                                      heuristic
                                    </span>
                                    <div className="flex-row">
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        disabled={a.busy}
                                        onClick={() =>
                                          acceptProposal(t.id, proposal.output)
                                        }
                                      >
                                        Yes, expect{" "}
                                        {JSON.stringify(proposal.output)}
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        disabled={a.busy}
                                        onClick={() =>
                                          void a.run(
                                            `/v1/analyses/${report.job_id}/contracts/decision`,
                                            {
                                              test_id: t.id,
                                              expected: proposal.output,
                                              reviewer: "workbench-user",
                                            },
                                          )
                                        }
                                      >
                                        No
                                      </Button>
                                    </div>
                                  </>
                                ) : null}

                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={a.busy}
                                  onClick={() => confirm(t.id)}
                                >
                                  Edit expected
                                </Button>
                                {t.domain !== "CONFIRMED" ? (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    disabled={a.busy}
                                    onClick={() =>
                                      void a.run(
                                        `/v1/analyses/${report.job_id}/contracts/domain`,
                                        {
                                          test_ids: [t.id],
                                          reviewer: "workbench-user",
                                        },
                                      )
                                    }
                                  >
                                    Confirm input domain
                                  </Button>
                                ) : null}
                                {details.actions ? (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    disabled={a.busy}
                                    onClick={() =>
                                      investigate("replay", { test_id: t.id })
                                    }
                                  >
                                    <RotateCcw size={11} />
                                    Replay
                                  </Button>
                                ) : null}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Counterexample Studio"
                  data={details.witness || report.structure.minimal_witness}
                  action={can("witness") ? "witness" : undefined}
                  busy={a.busy}
                  run={investigate}
                />
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Metamorphic Shield"
                  data={details.metamorphic}
                  action={can("metamorphic") ? "metamorphic" : undefined}
                  busy={a.busy}
                  run={investigate}
                />
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Replay"
                  data={details.replay}
                  busy={a.busy}
                  run={investigate}
                />
              </>
            ) : null}
            {workspace === "Repair Arena" ? (
              <>
                <div className="page-intro">
                  <div>
                    <h2>Candidate tournament</h2>
                    <p className="intro-copy">
                      Same frozen tests. Explicit gates. Correctness before
                      footprint.
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={a.busy}
                    onClick={() => modal("candidate")}
                  >
                    Validate your own candidate
                  </Button>
                </div>
                <div className="flex-row mb-4">
                  <Badge>
                    {report.model.llm_status === "DISABLED_NO_CONFIGURATION"
                      ? "LOCAL TEMPLATES / NO LLM KEY"
                      : String(report.model.llm_status || "LLM NOT RUN")}
                  </Badge>
                  <span className="text-[10px] muted">
                    Deterministic repair remains available without an external
                    provider.
                  </span>
                </div>
                <div className="candidate-strip">
                  {report.candidates.map((c, i) => (
                    <button
                      key={c.id}
                      className="panel candidate-option"
                      aria-pressed={candidate?.id === c.id}
                      onClick={() => setSelected(i)}
                    >
                      <span className="label">
                        Candidate {i + 1}{" "}
                        <span className="gold">
                          / {c.changed_lines} changed lines
                        </span>
                      </span>
                      <p className="text-xs my-3">
                        {c.operator.replaceAll("_", " ").toLowerCase()}
                      </p>
                      <Badge tone={tone(c.verdict)}>{c.verdict}</Badge>
                    </button>
                  ))}
                </div>
                {candidate ? (
                  <>
                    <div className="arena-details">
                      <div className="panel editor-shell">
                        <div className="panel-heading">
                          <span className="label">
                            Original → candidate {selectedIndex + 1}
                          </span>
                          <code className="text-[9px] muted">
                            {candidate.id.slice(0, 12)}
                          </code>
                        </div>
                        <div className="diff-shell">
                          <PatchDiff
                            original={report.source}
                            modified={candidate.source}
                            theme={theme}
                          />
                        </div>
                      </div>
                      <section className="panel panel-body">
                        <h2 className="mb-4">
                          Why this repair{" "}
                          {candidate.verdict.startsWith("VALIDATED")
                            ? "survives"
                            : "does not win"}
                        </h2>
                        <Badge tone={tone(candidate.verdict)}>
                          {candidate.verdict}
                        </Badge>
                        <div className="mt-4">
                          {candidate.checks
                            .filter(
                              (c) =>
                                c.regression ||
                                c.original !== c.patched ||
                                c.gate === "syntax_security_applicability",
                            )
                            .slice(0, 9)
                            .map((check, index) => (
                              <div className="gate" key={index}>
                                <code className="text-[10px]">
                                  {caseLabel(check.test_id || check.gate)}
                                </code>
                                <span>
                                  {String(
                                    check.reason ||
                                      `${check.original} → ${check.patched}`,
                                  )}
                                </span>
                                {check.regression ? (
                                  <Badge tone="bad">REGRESSION</Badge>
                                ) : null}
                              </div>
                            ))}
                        </div>
                        <div className="metric-inline mt-3">
                          <span className="muted">
                            Historical operator prior
                          </span>
                          <code>{candidate.prior.toFixed(3)}</code>
                        </div>
                        <div className="metric-inline">
                          <span className="muted">Runtime conclusion</span>
                          <span className="text-[9px]">
                            {String(candidate.performance.status)}
                          </span>
                        </div>
                        <details className="mt-4">
                          <summary>Context, affected callers & timing</summary>
                          <Json
                            value={{
                              context: candidate.context,
                              performance: candidate.performance,
                            }}
                          />
                        </details>
                      </section>
                    </div>
                    <div className="panel table-scroll mt-5">
                      <table>
                        <thead>
                          <tr>
                            <th>Input</th>
                            <th>Original</th>
                            <th>Candidate</th>
                            <th>Gate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {report.tests.map((t) => (
                            <tr key={t.id}>
                              <td>
                                <code>
                                  {t.function}({JSON.stringify(t.args)})
                                </code>
                              </td>
                              <td>
                                <Badge
                                  tone={observationTone(t, originals.get(t.id))}
                                >
                                  {observationLabel(t, originals.get(t.id))}
                                </Badge>
                                <p className="mono text-[10px] mt-2">
                                  {observed(originals.get(t.id))}
                                </p>
                              </td>
                              <td>
                                <Badge
                                  tone={observationTone(t, patched.get(t.id))}
                                >
                                  {observationLabel(t, patched.get(t.id))}
                                </Badge>
                                <p className="mono text-[10px] mt-2">
                                  {observed(patched.get(t.id))}
                                </p>
                              </td>
                              <td className="muted">
                                {t.tier} / {t.domain}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <Empty
                    title="No eligible bounded repair"
                    copy="The analyzer found no applicable template. This remains an unresolved investigation; a user candidate can still be validated."
                  />
                )}
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Repair Tournament"
                  data={details.tournament}
                  busy={a.busy}
                  run={investigate}
                />
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Repair Risk Budget"
                  data={details.risk_budget}
                  busy={a.busy}
                  run={investigate}
                />
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Precedent comparison"
                  data={details.precedents}
                  action={can("precedents") ? "precedents" : undefined}
                  busy={a.busy}
                  run={investigate}
                />
              </>
            ) : null}
            {workspace === "Model Lab & Vault" ? (
              <>
                <div className="data-grid">
                  <section className="panel panel-body">
                    <div className="flex-row justify-between">
                      <h2>Model Lab</h2>
                      <Badge>
                        {String(report.model.status || "MODEL_UNAVAILABLE")}
                      </Badge>
                    </div>
                    <p className="intro-copy">
                      Small held-out cohorts. No measured ML localization
                      uplift.
                    </p>
                    <div className="metric-inline mt-4">
                      <span>Calibration</span>
                      <span className="text-[9px]">
                        {String(report.model.calibration || "UNAVAILABLE")}
                      </span>
                    </div>
                    <p className="hash mt-3">
                      Model {String(report.model.model_id || "unavailable")}
                    </p>
                    <ModelMetrics report={report} />
                    <details className="mt-5">
                      <summary>
                        Full metrics, family confusion matrices & cohort
                        manifest
                      </summary>
                      <Json
                        value={{
                          metrics: report.model.metrics,
                          cohorts: report.model.cohorts,
                        }}
                      />
                    </details>
                  </section>
                  <section className="panel panel-body">
                    <div className="flex-row justify-between">
                      <h2>Evidence Vault</h2>
                      <Download size={14} className="gold" />
                    </div>
                    <div className="mt-5">
                      {[
                        ["Source", report.source_hash],
                        ["Tests", report.test_revision],
                        ["Runner", report.runner.digest],
                        ["Model", report.model.model_id],
                      ].map(([key, value]) => (
                        <div className="mb-4" key={String(key)}>
                          <span className="label">{String(key)}</span>
                          <p className="hash mt-1">
                            {String(value || "Unavailable")}
                          </p>
                        </div>
                      ))}
                    </div>
                    <Button
                      size="sm"
                      onClick={() =>
                        downloadBundle(
                          `/api/v1/analyses/${report.job_id}/bundle`,
                        )
                      }
                    >
                      <Download size={12} />
                      Download replayable bundle
                    </Button>
                    <p className="text-[10px] muted mt-3">
                      Integrity hashes establish content identity, not proof of
                      correctness.
                    </p>
                  </section>
                </div>
                <div className="data-grid mt-5">
                  <section className="panel panel-body">
                    <h2 className="mb-5">Historical analogies</h2>
                    {report.precedents.length ? (
                      report.precedents.map((p) => (
                        <details
                          className="py-3 border-b border-[var(--border)]"
                          key={String(p.id)}
                        >
                          <summary>
                            <span className="gold mono mr-2">
                              {(Number(p.similarity) * 100).toFixed(1)}%
                            </span>
                            {String(p.edit_summary)
                              .replaceAll("_", " ")
                              .toLowerCase()}
                            <span className="label ml-2">TRAIN ONLY</span>
                          </summary>
                          <p className="hash">{String(p.id)}</p>
                          <pre>{String(p.diff)}</pre>
                          <p className="hash">{String(p.origin)}</p>
                        </details>
                      ))
                    ) : (
                      <p className="muted">
                        No eligible neighbor. Similarity never establishes
                        correctness.
                      </p>
                    )}
                  </section>
                  <section className="panel panel-body">
                    <h2 className="mb-5">Persisted event timeline</h2>
                    <Timeline events={a.events} />
                    <details className="mt-5">
                      <summary>Scope and execution limits</summary>
                      <Json value={report.limitations} />
                    </details>
                  </section>
                </div>
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Novelty Radar"
                  data={details.novelty}
                  busy={a.busy}
                  run={investigate}
                />
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Proof-Carrying Patch Ledger"
                  data={details.ledger}
                  action={can("ledger") ? "ledger" : undefined}
                  busy={a.busy}
                  run={investigate}
                />
                <Experiment
                  report={report}
                  onSource={chooseFinding}
                  title="Semantic Twin Challenge"
                  data={details.twin}
                  action={can("twin") ? "twin" : undefined}
                  busy={a.busy}
                  run={investigate}
                />
              </>
            ) : null}
          </>
        )}
        <footer className="workspace-footer">
          <div className="module-dots">
            {Array.from({ length: 8 }, (_, i) => {
              const entry = Object.entries(report?.outputs || {}).find(
                ([key]) => key.startsWith(`M${i + 1}_`),
              );
              return (
                <span key={i}>
                  <i
                    className={
                      entry &&
                      (entry[1] as { status: string }).status === "AVAILABLE"
                        ? "available"
                        : ""
                    }
                  />
                  M{i + 1}
                </span>
              );
            })}
          </div>
          <span>
            {a.job
              ? `Revision ${a.job.id.slice(0, 8)} · ${a.connection}`
              : "Source → structure → prediction → witness → repair → evidence"}
          </span>
          <span>
            Built for scrutiny. <span className="gold">Yuktik / SAMYAK</span>
          </span>
        </footer>
      </main>
      <input
        hidden
        ref={upload}
        type="file"
        accept=".py,text/x-python"
        aria-label="Python file"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (file) {
            if (file.size > 60000) a.setError("Source limit is 60 KB");
            else {
              edit(await file.text());
              a.setTests([]);
              a.setFixture(null);
            }
          }
          e.target.value = "";
        }}
      />
      {dialog ? (
        <div
          className="modal-backdrop"
          onClick={(e) => e.target === e.currentTarget && setDialog(null)}
        >
          <section
            ref={modalRef}
            role="dialog"
            aria-modal="true"
            aria-label={
              dialog === "confirmation"
                ? "Confirm exact behavior"
                : dialog === "candidate"
                  ? "Validate candidate"
                  : "Authored test manifest"
            }
            className="panel modal"
          >
            <div className="flex-row justify-between">
              <span className="label">
                {dialog === "confirmation"
                  ? "One exact expectation / new revision"
                  : dialog === "candidate"
                    ? "Independent candidate validation"
                    : "Explicit test contract"}
              </span>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close dialog"
                onClick={() => {
                  setDialog(null);
                  setTab("source");
                }}
              >
                <X size={15} />
              </Button>
            </div>
            {dialog === "confirmation" && confirmation ? (
              <>
                <h2>Confirm exact behavior</h2>
                <p className="mono text-xs">
                  {confirmation.function}({JSON.stringify(confirmation.args)})
                </p>
                <p className="muted text-xs">
                  Observed: {observed(originals.get(confirmation.id))}. Your
                  confirmation covers this tuple only.
                </p>
                <label htmlFor="expected-output" className="label block mt-5">
                  Expected output / JSON
                </label>
                <input
                  autoFocus
                  className="w-full mono mt-2"
                  id="expected-output"
                  value={expected}
                  onChange={(e) => setExpected(e.target.value)}
                />
                <div className="flex-row justify-end mt-5">
                  <Button variant="ghost" onClick={() => setDialog(null)}>
                    Cancel
                  </Button>
                  <Button
                    disabled={a.busy || !expected.trim()}
                    onClick={submitConfirmation}
                  >
                    <Check size={13} />
                    Confirm & rerun
                  </Button>
                </div>
              </>
            ) : dialog === "tests" ? (
              <>
                <h2>Authored tests, explicit expectations.</h2>
                <p className="muted text-xs">
                  Use JSON fields function, args, expected, has_expected: true,
                  tier: &quot;A&quot;, domain: &quot;CONFIRMED&quot;. Values are
                  validated by the API.
                </p>
                <textarea
                  autoFocus
                  aria-label="Authored tests JSON"
                  rows={12}
                  value={testDraft}
                  onChange={(e) => setTestDraft(e.target.value)}
                />
                <Button
                  onClick={() => {
                    try {
                      const parsed: unknown = JSON.parse(testDraft || "[]");
                      if (!Array.isArray(parsed))
                        throw new Error("Expected an array");
                      a.setTests(parsed as TestCase[]);
                      setDialog(null);
                      setTab("source");
                      a.setError("");
                    } catch (e) {
                      a.setError(String(e));
                    }
                  }}
                >
                  Apply test manifest
                </Button>
              </>
            ) : (
              <>
                <h2>Test your own repair.</h2>
                <p className="muted text-xs">
                  The original stays immutable. The full recorded suite runs
                  against the candidate.
                </p>
                <textarea
                  aria-label="Candidate source"
                  rows={15}
                  value={customPatch}
                  onChange={(e) => setCustomPatch(e.target.value)}
                />
                <Button
                  disabled={a.busy || !customPatch.trim()}
                  onClick={() => {
                    setDialog(null);
                    if (report)
                      void a.run(
                        `/v1/analyses/${report.job_id}/patches/validate`,
                        { source: customPatch },
                      );
                  }}
                >
                  Validate candidate
                </Button>
              </>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
function Timeline({
  events,
}: {
  events: { id: number; stage: string; message: string; timestamp: string }[];
}) {
  return (
    <div className="timeline">
      {events.map((e) => (
        <div className="timeline-row" key={e.id}>
          <time title={e.timestamp} dateTime={e.timestamp}>
            {new Date(e.timestamp).toLocaleTimeString("en-GB", {
              hour12: false,
            })}
          </time>
          <i className="stage-dot" />
          <div>
            <span className="capitalize">{e.stage.replaceAll("_", " ")}</span>
            <p>{e.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
function downloadBundle(path: string) {
  const link = document.createElement("a");
  link.href = path;
  link.download = "samyak-evidence.zip";
  link.click();
}
