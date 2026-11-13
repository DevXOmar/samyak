"use client";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Braces,
  Check,
  CircleDot,
  Download,
  FileCode2,
  FlaskConical,
  GitBranch,
  Layers3,
  Play,
  ShieldCheck,
  Upload,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  api,
  observed,
  observationLabel,
  observationTone,
  riskLabel,
  tone,
  type AnalysisRequest,
  type Job,
  type PipelineEvent,
  type Report,
  type TestCase,
} from "@/lib/client";
const CodeEditor = dynamic(() => import("@/components/code-editor"), {
  ssr: false,
});
const TABS = [
  "Findings",
  "Generated tests",
  "Repair tournament",
  "Structure",
  "Models & history",
] as const;
type Tab = (typeof TABS)[number];
const EMPTY: Report["findings"] = [];

export default function Workbench() {
  const [source, setSource] = useState("");
  const [tests, setTests] = useState<TestCase[]>([]);
  const [fixture, setFixture] = useState<AnalysisRequest["fixture"]>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>("Findings");
  const [line, setLine] = useState<number | null>(null);
  const [selected, setSelected] = useState(0);
  const [confirmTest, setConfirmTest] = useState<string | null>(null);
  const [expected, setExpected] = useState("");
  const [customPatch, setCustomPatch] = useState("");
  const [testJson, setTestJson] = useState("");
  const upload = useRef<HTMLInputElement>(null);
  const stream = useRef<EventSource | null>(null);
  const activeJob = useRef<string | null>(null);
  useEffect(() => () => stream.current?.close(), []);

  async function watch(next: Job) {
    stream.current?.close();
    activeJob.current = next.id;
    setJob(next);
    setReport(null);
    setEvents([]);
    setSelected(0);
    setConfirmTest(null);
    setBusy(true);
    const sse = new EventSource(`/api/v1/analyses/${next.id}/events`);
    stream.current = sse;
    sse.addEventListener("stage", (e) => {
      const ev = JSON.parse((e as MessageEvent).data) as PipelineEvent;
      setEvents((old) =>
        old.some((v) => v.id === ev.id) ? old : [...old, ev],
      );
      setJob((old) =>
        old
          ? {
              ...old,
              stage: ev.stage,
              status:
                ev.stage === "completed"
                  ? "COMPLETED"
                  : ev.stage === "failed"
                    ? "FAILED"
                    : ev.stage === "queued"
                      ? "QUEUED"
                      : "RUNNING",
            }
          : old,
      );
    });
    sse.addEventListener("done", () => {
      sse.close();
      void finish(next.id);
    });
    sse.onerror = () => {
      setError(
        "Live connection interrupted. Reconnecting to the persisted job…",
      );
    };
  }
  async function finish(id: string) {
    try {
      const current = await api<Job>(`/v1/analyses/${id}`);
      if (activeJob.current !== id) return;
      setJob(current);
      if (current.status === "FAILED")
        throw new Error(current.error || "Worker failed");
      const result = await api<Report>(`/v1/analyses/${id}/report`);
      if (activeJob.current !== id) return;
      setReport(result);
      setCustomPatch(result.candidates[0]?.source || result.source);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      if (activeJob.current === id) setBusy(false);
    }
  }
  async function run(
    path = "/v1/analyses",
    body: unknown = { source, tests, fixture },
  ) {
    setError("");
    setBusy(true);
    try {
      await watch(await api<Job>(path, body));
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }
  async function loadFixture(name: NonNullable<AnalysisRequest["fixture"]>) {
    try {
      const data = await api<AnalysisRequest>(`/v1/fixtures/${name}`);
      setSource(data.source);
      setTests(data.tests || []);
      setFixture(name);
      setTestJson(JSON.stringify(data.tests || [], null, 2));
      setReport(null);
      setJob(null);
      setEvents([]);
      setLine(null);
    } catch (e) {
      setError(String(e));
    }
  }
  function focus(at: number) {
    setLine(at);
    window.scrollTo({ top: 100, behavior: "smooth" });
  }
  const candidate = report?.candidates[selected];
  const resultById = new Map(
    report?.original_results.map((r) => [r.test_id, r]),
  );
  const patchedById = new Map(candidate?.results.map((r) => [r.test_id, r]));
  const confirmation = report?.tests.find((t) => t.id === confirmTest);
  const nodes = report?.structure?.graph as
    | { nodes?: unknown[]; edges?: unknown[] }
    | undefined;
  const modelMetrics = report?.model?.metrics;

  return (
    <div className="min-h-screen">
      <header className="border-b border-zinc-800 bg-[#141619] px-5 lg:px-10 h-18 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-teal-400 text-zinc-950 flex items-center justify-center">
            <Layers3 size={19} />
          </div>
          <span className="text-lg tracking-[.2em] font-bold">SAMYAK</span>
          <span className="ml-4 border-l border-zinc-700 pl-4 text-xs text-zinc-500 hidden sm:block">
            YUKTIK / ENGINEERING WORKBENCH
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <span className="size-1.5 rounded-full bg-teal-400" /> Python 3.11{" "}
          <Badge>PHASE 01</Badge>
        </div>
      </header>
      <main className="max-w-[1600px] mx-auto px-4 py-7 sm:px-7 lg:px-10 lg:py-9">
        <div className="flex flex-wrap justify-between items-end gap-4 mb-7">
          <div>
            <p className="label text-teal-400 mb-3">
              Predict → investigate → validate
            </p>
            <h1 className="text-3xl sm:text-4xl font-medium tracking-tight">
              Find the fault. Keep the proof.
            </h1>
            <p className="text-sm text-zinc-400 mt-3 max-w-2xl">
              Structural analysis, trained predictions and isolated execution.
              Every repair carries its evidence.
            </p>
          </div>
          <Button variant="outline" disabled={!report} asChild={!!report}>
            {report ? (
              <a href={`/api/v1/analyses/${report.job_id}/bundle`}>
                <Download size={15} /> Evidence bundle
              </a>
            ) : (
              <span className="flex items-center gap-2">
                <Download size={15} /> Evidence bundle
              </span>
            )}
          </Button>
        </div>
        <div className="flex flex-wrap gap-2 items-center mb-5">
          <span className="label mr-2">Source fixtures</span>
          {(
            [
              ["binary_search", "A · Boundary + reference"],
              ["average", "B · Unknown contract"],
              ["caller_regression", "C · Caller regression"],
            ] as const
          ).map(([name, title]) => (
            <Button
              key={name}
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={() => void loadFixture(name)}
            >
              <FileCode2 size={13} />
              {title}
            </Button>
          ))}
          <span className="text-[11px] text-zinc-600 ml-1">
            Sources only. Analyze to run.
          </span>
        </div>
        {error ? (
          <div
            role="alert"
            className="mb-4 border border-rose-900 bg-rose-950/40 rounded-lg p-3 text-sm text-rose-200"
          >
            {error}
          </div>
        ) : null}
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.55fr)_minmax(330px,1fr)] gap-5">
          <section className="panel">
            <div className="px-4 h-12 flex items-center justify-between border-b border-zinc-800">
              <span className="text-xs text-zinc-300 flex gap-2 items-center">
                <FileCode2 size={14} className="text-teal-400" />
                {fixture ? `${fixture}.py` : "submission.py"}
                <span className="text-zinc-600 ml-3">PYTHON</span>
              </span>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => upload.current?.click()}
              >
                <Upload size={13} /> Upload .py
              </Button>
              <input
                ref={upload}
                aria-label="Upload Python source"
                type="file"
                accept=".py,text/x-python"
                hidden
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    if (file.size > 60000) {
                      setError("Source limit is 60 KB");
                      return;
                    }
                    setSource(await file.text());
                    setTests([]);
                    setTestJson("");
                    setFixture(null);
                    setReport(null);
                  }
                  e.target.value = "";
                }}
              />
            </div>
            <CodeEditor
              value={source}
              onChange={(v) => {
                setSource(v);
                setLine(null);
              }}
              findings={report?.source === source ? report.findings : EMPTY}
              line={line}
            />
            <div className="border-t border-zinc-800 p-4 flex flex-wrap justify-between items-center gap-3">
              <span className="text-xs text-zinc-500">
                {source.split("\n").length} lines ·{" "}
                {new TextEncoder().encode(source).length} bytes · {tests.length}{" "}
                authored tests
              </span>
              <Button
                disabled={busy || !source.trim()}
                onClick={() => void run()}
              >
                <Play size={14} fill="currentColor" />
                {busy ? "Analyzing…" : "Analyze source"}
              </Button>
            </div>
            <details className="border-t border-zinc-800 p-4">
              <summary>Authored tests / explicit expected outputs</summary>
              <p className="text-xs text-zinc-500 mt-3">
                JSON array: function, args, expected, has_expected: true, tier:
                &quot;A&quot;, domain: &quot;CONFIRMED&quot;. Source assertions
                are also extracted.
              </p>
              <textarea
                aria-label="Authored tests JSON"
                className="w-full mono mt-3 text-xs"
                rows={5}
                value={testJson}
                onChange={(e) => setTestJson(e.target.value)}
              />
              <Button
                className="mt-2"
                variant="outline"
                size="sm"
                onClick={() => {
                  try {
                    const parsed = JSON.parse(testJson || "[]");
                    if (!Array.isArray(parsed))
                      throw new Error("Tests must be an array");
                    setTests(parsed as TestCase[]);
                    setError("");
                  } catch (e) {
                    setError(String(e));
                  }
                }}
              >
                Apply test manifest
              </Button>
            </details>
          </section>
          <aside className="flex flex-col gap-4">
            <section className="panel p-5">
              <div className="flex justify-between items-center mb-5">
                <span className="label">Investigation status</span>
                <Badge tone={tone(job?.status)}>
                  {job?.status || "AWAITING SOURCE"}
                </Badge>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-10 border border-zinc-700 rounded-full flex items-center justify-center text-teal-400">
                  <GitBranch size={19} />
                </div>
                <div>
                  <p className="text-base font-medium">
                    {job?.stage.replaceAll("_", " ") || "Ready when you are"}
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">
                    {job
                      ? `Job ${job.id.slice(0, 12)} · immutable revision`
                      : "Paste Python or choose a source fixture"}
                  </p>
                </div>
              </div>
              <div
                aria-live="polite"
                className="mt-5 max-h-47 overflow-y-auto space-y-3"
              >
                {events.length ? (
                  events.map((e) => (
                    <div key={e.id} className="flex gap-3 text-xs">
                      <Check
                        className="shrink-0 text-teal-500 mt-0.5"
                        size={12}
                      />
                      <div>
                        <span className="text-zinc-300 capitalize">
                          {e.stage}
                        </span>
                        <p className="text-zinc-500 leading-relaxed mt-0.5">
                          {e.message}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs leading-relaxed text-zinc-500">
                    The timeline streams persisted worker events. Predictions
                    and execution results appear after a real analysis.
                  </p>
                )}
              </div>
            </section>
            <div className="grid grid-cols-2 gap-3">
              <section className="panel p-4">
                <div className="label">Highest function risk</div>
                <p className="text-3xl tracking-tight mt-3 text-teal-300">
                  {riskLabel(report?.overall_risk)}
                </p>
                <p className="text-[10px] mt-2 text-zinc-500">
                  Learned training-label risk
                </p>
              </section>
              <section className="panel p-4">
                <div className="label">Evidence severity</div>
                <p className="text-2xl mt-3">{report?.severity || "—"}</p>
                <p className="text-[10px] mt-2 text-zinc-500">
                  Impact policy, separate from ML
                </p>
              </section>
            </div>
            <section className="panel p-4 flex-1">
              <div className="flex justify-between mb-4">
                <span className="label">Decision</span>
                <ShieldCheck size={15} className="text-zinc-500" />
              </div>
              <Badge tone={tone(report?.verdict)}>
                {report?.verdict || "NOT YET ASSESSED"}
              </Badge>
              <p className="text-xs text-zinc-500 leading-relaxed mt-3">
                {report?.runner.status === "EXECUTION_UNAVAILABLE"
                  ? "Execution is disabled until Docker and the fixed runner image are available."
                  : "Test validation applies to the recorded cases. An unconfirmed input domain or guessed output cannot certify a patch."}
              </p>
              <p className="text-[10px] text-zinc-600 mt-3">
                Docker-only isolation · development-grade
              </p>
            </section>
          </aside>
        </div>
        <div
          className="mt-7 flex gap-1 border-b border-zinc-800 overflow-x-auto"
          role="tablist"
          aria-label="Analysis evidence"
        >
          {TABS.map((name, index) => (
            <button
              key={name}
              id={`tab-${index}`}
              role="tab"
              aria-selected={tab === name}
              aria-controls={`panel-${index}`}
              onClick={() => setTab(name)}
              className={`px-4 py-3 text-xs whitespace-nowrap border-b-2 ${tab === name ? "border-teal-400 text-teal-300" : "border-transparent text-zinc-500 hover:text-zinc-300"}`}
            >
              {name}
              {name === "Findings" && report
                ? ` / ${report.findings.length}`
                : ""}
            </button>
          ))}
        </div>
        <section
          id={`panel-${TABS.indexOf(tab)}`}
          role="tabpanel"
          aria-labelledby={`tab-${TABS.indexOf(tab)}`}
          className="mt-5 min-h-60"
        >
          {!report ? (
            <div className="panel p-12 text-center">
              <Braces size={28} className="mx-auto text-zinc-600 mb-4" />
              <p className="text-sm text-zinc-300">
                {busy
                  ? "Investigation in progress"
                  : "Evidence starts with your code"}
              </p>
              <p className="text-xs text-zinc-500 mt-2">
                {busy
                  ? "The worker is building this report. Follow its stages above."
                  : "Run an analysis to inspect findings, generated cases, patches and provenance."}
              </p>
            </div>
          ) : (
            <>
              {report.source !== source ? (
                <p className="text-xs text-amber-300 mb-4">
                  This report belongs to an earlier immutable source revision.
                  Analyze again to assess the editor contents.
                </p>
              ) : null}
              {tab === "Findings" ? (
                <div className="grid lg:grid-cols-[1fr_340px] gap-5">
                  <div className="space-y-3">
                    {report.findings.length ? (
                      report.findings.map((f) => (
                        <button
                          key={f.id}
                          onClick={() => focus(f.span.start_line)}
                          className="panel w-full p-5 text-left hover:border-zinc-500 transition-colors"
                        >
                          <div className="flex flex-wrap gap-2 items-center">
                            <Badge
                              tone={f.severity === "HIGH" ? "bad" : "warn"}
                            >
                              {f.severity}
                            </Badge>
                            <span className="text-xs mono text-zinc-400">
                              {f.function} : {f.span.start_line}
                            </span>
                            <ArrowUpRight
                              className="ml-auto text-zinc-500"
                              size={15}
                            />
                          </div>
                          <h3 className="text-sm mt-3">{f.rule_id}</h3>
                          <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                            {f.explanation}
                          </p>
                          <div className="mt-3">
                            <Badge>{f.evidence}</Badge>
                            <p className="text-[11px] text-zinc-600 mt-2">
                              {f.qualification}
                            </p>
                          </div>
                        </button>
                      ))
                    ) : (
                      <div className="panel p-8 text-sm text-zinc-500">
                        No supported rule findings. This does not prove absence
                        of defects.
                      </div>
                    )}
                  </div>
                  <div className="space-y-4">
                    <div className="panel p-4">
                      <p className="label mb-4">Function predictions</p>
                      {report.functions.map((f) => (
                        <div
                          key={`${f.name}-${f.span.start_line}`}
                          className="py-3 border-b border-zinc-800"
                        >
                          <button
                            onClick={() => focus(f.span.start_line)}
                            className="flex justify-between w-full text-xs"
                          >
                            <code>{f.name}</code>
                            <span className="text-teal-300">
                              {riskLabel(f.risk)}
                            </span>
                          </button>
                          <div className="h-1 rounded bg-zinc-800 my-2">
                            <div
                              className="h-1 rounded bg-teal-500"
                              style={{ width: `${(f.risk || 0) * 100}%` }}
                            />
                          </div>
                          <p className="text-[10px] text-zinc-500">
                            {f.family || "Family unavailable"}
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="panel p-4">
                      <p className="label mb-4">Suspicious statements</p>
                      {report.localization.slice(0, 8).map((r, i) => (
                        <button
                          key={`${r.function}-${r.line}`}
                          className="w-full flex justify-between text-xs py-2 text-zinc-400"
                          onClick={() => focus(Number(r.line))}
                        >
                          <span>
                            {i + 1}. Line {String(r.line)} ·{" "}
                            {String(r.function)}
                          </span>
                          <span className="text-teal-400">
                            {Number(r.score).toFixed(3)}
                          </span>
                        </button>
                      ))}
                      <details className="mt-3">
                        <summary>Each ranking signal</summary>
                        <pre>
                          {JSON.stringify(
                            report.localization.slice(0, 12),
                            null,
                            2,
                          )}
                        </pre>
                      </details>
                    </div>
                  </div>
                </div>
              ) : null}
              {tab === "Generated tests" ? (
                <div className="space-y-4">
                  <div className="flex justify-between flex-wrap gap-3 items-center">
                    <div>
                      <h2 className="text-lg">Inputs, oracles & witnesses</h2>
                      <p className="text-xs text-zinc-500 mt-2">
                        A: exact expectation · B: declared property · I:
                        operational fault · C: exploratory. Domain is a separate
                        gate.
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={busy}
                      onClick={() =>
                        void run(`/v1/analyses/${report.job_id}/tests`, {})
                      }
                    >
                      <FlaskConical size={14} /> New test revision
                    </Button>
                  </div>
                  <div className="panel overflow-x-auto">
                    <table>
                      <thead>
                        <tr>
                          <th>Function / input</th>
                          <th>Oracle / domain</th>
                          <th>Original observation</th>
                          <th>Expectation</th>
                          <th>Exact-case confirmation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.tests.map((t) => {
                          const r = resultById.get(t.id);
                          return (
                            <tr key={t.id}>
                              <td>
                                <code>
                                  {t.function}({JSON.stringify(t.args)})
                                </code>
                                <p className="text-[10px] text-zinc-600 mt-2 max-w-65">
                                  {t.reason}
                                </p>
                              </td>
                              <td>
                                <Badge>{t.tier}</Badge>
                                <p className="text-[10px] mt-2 text-zinc-500">
                                  {t.domain}
                                </p>
                              </td>
                              <td>
                                <Badge tone={observationTone(t, r)}>
                                  {observationLabel(t, r)}
                                </Badge>
                                <p className="mono text-[11px] mt-2 max-w-60 break-all">
                                  {observed(r)}
                                </p>
                              </td>
                              <td className="mono">
                                {t.has_expected
                                  ? JSON.stringify(t.expected)
                                  : t.property || "No output oracle"}
                              </td>
                              <td>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={busy}
                                  onClick={() => {
                                    setConfirmTest(t.id);
                                    setExpected(
                                      t.has_expected
                                        ? JSON.stringify(t.expected)
                                        : "",
                                    );
                                  }}
                                >
                                  Confirm output
                                </Button>
                                {t.domain !== "CONFIRMED" ? (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="mt-2 block"
                                    disabled={busy}
                                    onClick={() =>
                                      void run(
                                        `/v1/analyses/${report.job_id}/contracts/domain`,
                                        {
                                          test_ids: [t.id],
                                          reviewer: "workbench-user",
                                        },
                                      )
                                    }
                                  >
                                    Accept exact input domain
                                  </Button>
                                ) : null}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  {confirmation ? (
                    <div className="panel p-5 border-teal-800">
                      <h3 className="text-sm mb-3">
                        Confirm one exact expected result
                      </h3>
                      <p className="mono text-xs mb-3">
                        {confirmation.function}(
                        {JSON.stringify(confirmation.args)})
                      </p>
                      <label
                        className="text-xs text-zinc-400 block mb-2"
                        htmlFor="expected-output"
                      >
                        Expected output (JSON)
                      </label>
                      <div className="flex gap-3">
                        <input
                          id="expected-output"
                          className="flex-1 min-w-0 mono text-sm"
                          value={expected}
                          onChange={(e) => setExpected(e.target.value)}
                        />
                        <Button
                          disabled={busy || !expected.trim()}
                          onClick={() => {
                            try {
                              const value: unknown = JSON.parse(expected);
                              void run(
                                `/v1/analyses/${report.job_id}/contracts/confirm`,
                                {
                                  function: confirmation.function,
                                  args: confirmation.args,
                                  kwargs: confirmation.kwargs,
                                  expected: value,
                                  reviewer: "workbench-user",
                                },
                              );
                            } catch (e) {
                              setError(String(e));
                            }
                          }}
                        >
                          Confirm & rerun
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => setConfirmTest(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                      <p className="text-xs text-zinc-500 mt-3">
                        Creates a versioned A oracle for this tuple. Earlier
                        reports remain immutable.
                      </p>
                    </div>
                  ) : null}
                  <details className="panel p-5">
                    <summary>
                      Inferred strategies, trial outcomes & smallest witness
                    </summary>
                    <pre>
                      {JSON.stringify(
                        {
                          inference: report.inference,
                          witness: report.structure.minimal_witness,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                </div>
              ) : null}
              {tab === "Repair tournament" ? (
                <div className="space-y-5">
                  <div className="flex gap-3 flex-wrap">
                    {report.candidates.map((c, i) => (
                      <button
                        key={c.id}
                        onClick={() => setSelected(i)}
                        className={`panel p-4 text-left ${selected === i ? "border-teal-600" : ""}`}
                      >
                        <span className="label">
                          Candidate {i + 1} · {c.changed_lines} changed lines
                        </span>
                        <p className="text-xs my-2">{c.operator}</p>
                        <Badge tone={tone(c.verdict)}>{c.verdict}</Badge>
                      </button>
                    ))}
                  </div>
                  {candidate ? (
                    <>
                      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-4">
                        <div className="panel p-5">
                          <p className="label mb-4">Immutable candidate diff</p>
                          <pre className="text-zinc-300">
                            {candidate.diff.split("\n").map((text, i) => (
                              <span
                                className={`block ${text.startsWith("+") ? "text-teal-300 bg-teal-950/40" : text.startsWith("-") ? "text-rose-300 bg-rose-950/30" : ""}`}
                                key={i}
                              >
                                {text || " "}
                              </span>
                            ))}
                          </pre>
                        </div>
                        <div className="panel p-5">
                          <p className="label mb-4">
                            Validation & optimization
                          </p>
                          <Badge tone={tone(candidate.verdict)}>
                            {candidate.verdict}
                          </Badge>
                          <p className="text-xs text-zinc-400 mt-4">
                            Precedent operator prior:{" "}
                            {candidate.prior.toFixed(3)}
                          </p>
                          <p className="text-xs text-amber-300 mt-3">
                            {String(candidate.performance.status)}
                          </p>
                          <details className="mt-4">
                            <summary>Runtime samples and context</summary>
                            <pre>
                              {JSON.stringify(
                                {
                                  performance: candidate.performance,
                                  context: candidate.context,
                                },
                                null,
                                2,
                              )}
                            </pre>
                          </details>
                        </div>
                      </div>
                      <div className="panel overflow-x-auto">
                        <table>
                          <thead>
                            <tr>
                              <th>Input</th>
                              <th>Original</th>
                              <th>Patched</th>
                              <th>Gate</th>
                            </tr>
                          </thead>
                          <tbody>
                            {report.tests.map((t) => {
                              const a = resultById.get(t.id),
                                b = patchedById.get(t.id);
                              return (
                                <tr key={t.id}>
                                  <td className="mono">
                                    {t.function}({JSON.stringify(t.args)})
                                  </td>
                                  <td>
                                    <Badge tone={observationTone(t, a)}>
                                      {observationLabel(t, a)}
                                    </Badge>
                                    <p className="mono mt-2">{observed(a)}</p>
                                  </td>
                                  <td>
                                    <Badge tone={observationTone(t, b)}>
                                      {observationLabel(t, b)}
                                    </Badge>
                                    <p className="mono mt-2">{observed(b)}</p>
                                  </td>
                                  <td className="text-zinc-500">
                                    {t.tier} / {t.domain}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : (
                    <div className="panel p-8 text-sm text-zinc-500">
                      No bounded applicable template was found. Predictions are
                      available; the repair remains unresolved.
                    </div>
                  )}
                  <details className="panel p-5">
                    <summary>Validate a candidate you provide</summary>
                    <label
                      className="block text-xs text-zinc-500 mt-3 mb-2"
                      htmlFor="custom-patch"
                    >
                      Complete candidate source; validated as a new immutable
                      job
                    </label>
                    <textarea
                      id="custom-patch"
                      className="w-full mono text-xs"
                      rows={10}
                      value={customPatch}
                      onChange={(e) => setCustomPatch(e.target.value)}
                    />
                    <Button
                      className="mt-3"
                      disabled={busy || !customPatch.trim()}
                      onClick={() =>
                        void run(
                          `/v1/analyses/${report.job_id}/patches/validate`,
                          { source: customPatch },
                        )
                      }
                    >
                      Validate candidate
                    </Button>
                  </details>
                </div>
              ) : null}
              {tab === "Structure" ? (
                <div className="space-y-4">
                  <div className="grid sm:grid-cols-3 gap-4">
                    {[
                      ["Functions", report.functions.length],
                      ["Graph nodes", nodes?.nodes?.length || 0],
                      ["Graph edges", nodes?.edges?.length || 0],
                    ].map(([label, value]) => (
                      <div className="panel p-5" key={label}>
                        <p className="label">{label}</p>
                        <p className="text-3xl mt-3">{value}</p>
                      </div>
                    ))}
                  </div>
                  <details className="panel p-5" open>
                    <summary>AST summary, CFG, def-use and call graph</summary>
                    <pre className="max-h-120 overflow-auto">
                      {JSON.stringify(report.structure, null, 2)}
                    </pre>
                  </details>
                  <details className="panel p-5">
                    <summary>Static Ruff / Bandit observations</summary>
                    <pre className="max-h-100 overflow-auto">
                      {JSON.stringify(report.scanners, null, 2)}
                    </pre>
                  </details>
                </div>
              ) : null}
              {tab === "Models & history" ? (
                <div className="grid lg:grid-cols-2 gap-5">
                  <div className="panel p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap size={16} className="text-teal-400" />
                      <h2 className="text-sm">Independent model provenance</h2>
                    </div>
                    <Badge>{String(report.model.status)}</Badge>
                    <p className="text-xs text-zinc-400 mt-4">
                      {String(report.model.calibration)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-3 break-all">
                      Model ID: {String(report.model.model_id || "Unavailable")}
                    </p>
                    <p className="text-xs text-amber-300 mt-4">
                      {String(report.model.novelty)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-2">
                      Historical unfamiliarity does not prove a bug.
                    </p>
                    <details className="mt-4">
                      <summary>
                        Measured metrics, confusion matrices & ML ablation
                      </summary>
                      <pre className="max-h-120 overflow-auto">
                        {JSON.stringify(
                          modelMetrics || { status: "UNAVAILABLE" },
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                    <details className="mt-4">
                      <summary>Frozen cohort manifest</summary>
                      <pre className="max-h-80 overflow-auto">
                        {JSON.stringify(report.model.cohorts || {}, null, 2)}
                      </pre>
                    </details>
                  </div>
                  <div className="space-y-3">
                    <p className="label">Train-only precedent engine</p>
                    {report.precedents.length ? (
                      report.precedents.map((p) => (
                        <div className="panel p-4" key={String(p.id)}>
                          <div className="flex justify-between gap-3">
                            <code className="text-xs break-all text-zinc-300">
                              {String(p.id)}
                            </code>
                            <Badge>
                              {(Number(p.similarity) * 100).toFixed(1)}% SIM
                            </Badge>
                          </div>
                          <p className="text-xs text-zinc-500 mt-3">
                            {String(p.edit_summary)} · {String(p.domain)}
                          </p>
                          <details className="mt-3">
                            <summary>
                              Historical analogy · not an oracle
                            </summary>
                            <pre>{String(p.diff)}</pre>
                          </details>
                        </div>
                      ))
                    ) : (
                      <div className="panel p-6 text-sm text-zinc-500">
                        No eligible historical precedent.
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </>
          )}
        </section>
        <footer className="border-t border-zinc-800 mt-8 pt-5 pb-2">
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
            {Object.entries(
              report?.outputs ||
                Object.fromEntries(
                  Array.from({ length: 8 }, (_, i) => [
                    `M${i + 1}`,
                    { status: "UNAVAILABLE" },
                  ]),
                ),
            ).map(([key, value]) => (
              <div className="text-[10px] text-zinc-600" key={key}>
                <span className="flex items-center gap-1">
                  <CircleDot
                    size={9}
                    className={
                      (value as { status?: string }).status === "AVAILABLE"
                        ? "text-teal-500"
                        : "text-zinc-600"
                    }
                  />
                  {key.split("_").slice(0, 2).join(" ")}
                </span>
                <span className="block mt-1">
                  {String((value as { status?: string }).status)}
                </span>
              </div>
            ))}
          </div>
          <details className="mt-5">
            <summary>Scope, evidence limits & source hashes</summary>
            <pre>
              {JSON.stringify(
                report
                  ? {
                      source_hash: report.source_hash,
                      test_revision: report.test_revision,
                      limitations: report.limitations,
                    }
                  : { status: "No report" },
                null,
                2,
              )}
            </pre>
          </details>
        </footer>
      </main>
    </div>
  );
}
