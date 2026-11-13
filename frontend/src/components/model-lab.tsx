"use client";
import { useState } from "react";
import type { Report, PipelineEvent } from "@/lib/client";
import { riskLabel } from "@/lib/client";
import ModelMetrics from "./model-metrics";
import IntelligencePanel from "./intelligence-panel";
import { Button } from "./ui/button";
export default function ModelLab({
  report,
  events,
  busy,
  run,
  onSource,
  onAtlas,
  download,
}: {
  report: Report;
  events: PipelineEvent[];
  busy: boolean;
  run: (action: string) => void;
  onSource: (line: number) => void;
  onAtlas: (line: number) => void;
  download: () => void;
}) {
  const [selected, setSelected] = useState("");
  const fn =
    report.functions.find((f) => f.name === selected) ||
    [...report.functions].sort((a, b) => (b.risk ?? -1) - (a.risk ?? -1))[0];
  const novelty = report.intelligence.novelty as
    | { status?: string; abstain?: boolean; reason?: string }
    | undefined;
  const can = (action: string) =>
    Array.isArray(report.intelligence.actions) &&
    report.intelligence.actions.includes(action);
  const experiments = [
    ["Novelty Radar", "novelty", undefined],
    ["Proof-Carrying Patch Ledger", "ledger", "ledger"],
    ["Semantic Twin Challenge", "twin", "twin"],
  ] as const;
  return (
    <div className="model-lab-stack">
      <section className="panel panel-body">
        <div className="lab-evidence-heading">
          <h2>Model Performance</h2>
          <span className="label">Held-out evaluation</span>
        </div>
        <ModelMetrics report={report} />
      </section>
      <section className="panel panel-body">
        <h2>Code Intelligence</h2>
        <p className="intro-copy">
          {report.functions.length} analyzed functions · estimates are not
          defect certainty.
        </p>
        {fn ? (
          <>
            <div className="function-risk-list">
              {[...report.functions]
                .sort((a, b) => (b.risk ?? -1) - (a.risk ?? -1))
                .map((f) => (
                  <button
                    key={`${f.name}:${f.span.start_line}`}
                    aria-pressed={fn === f}
                    onClick={() => setSelected(f.name)}
                  >
                    <code>
                      {f.name} · L{f.span.start_line}
                    </code>
                    <span className="metric-track">
                      <i style={{ width: `${(f.risk || 0) * 100}%` }} />
                    </span>
                    <strong>{riskLabel(f.risk)}</strong>
                  </button>
                ))}
            </div>
            <div className="compact-function-detail">
              <label>
                Selected function{" "}
                <select
                  aria-label="Model function"
                  value={fn.name}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {report.functions.map((f) => (
                    <option
                      key={`${f.name}:${f.span.start_line}`}
                      value={f.name}
                    >
                      {f.name} · L{f.span.start_line}
                    </option>
                  ))}
                </select>
              </label>
              <p>
                Risk estimate: {riskLabel(fn.risk)} · source L
                {fn.span.start_line}–{fn.span.end_line}
              </p>
              <p className="metric-footnote">
                Observed AST inputs:{" "}
                {Object.entries(fn.features)
                  .filter(([k]) =>
                    [
                      "lines",
                      "calls",
                      "branches",
                      "parameters",
                      "complexity",
                    ].includes(k),
                  )
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}
                . Learned prediction uses AST features and train-fitted TF-IDF;
                no causal feature attribution is recorded.
              </p>
              <div className="flex-row">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    onSource(
                      report.findings.find((f) => f.function === fn.name)?.span
                        .start_line || fn.span.start_line,
                    )
                  }
                >
                  Inspect in Workbench
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    onAtlas(
                      Number(
                        report.localization.find((r) => r.function === fn.name)
                          ?.line,
                      ) || fn.span.start_line,
                    )
                  }
                >
                  Explore in Fault Atlas
                </Button>
              </div>
              <details className="lab-disclosure">
                <summary>Prediction diagnostics & static findings</summary>
                <p>
                  Predicted family: {fn.family || "Unavailable"} · novelty:{" "}
                  {novelty?.status || "Unavailable"} · abstention:{" "}
                  {novelty?.abstain == null
                    ? "Unavailable"
                    : String(novelty.abstain)}
                </p>
                <p>{novelty?.reason}</p>
                <p className="intro-copy">
                  Static rules are independent hypotheses, not learned
                  probabilities.
                </p>
                {report.findings
                  .filter((f) => f.function === fn.name)
                  .map((f) => (
                    <button
                      className="trace-link"
                      key={f.id}
                      onClick={() => onSource(f.span.start_line)}
                    >
                      L{f.span.start_line} · {f.rule_id} · {f.evidence}
                    </button>
                  ))}
              </details>
            </div>
          </>
        ) : (
          <p className="intro-copy">
            ML risk: Not applicable to script-only source. Execution and static
            evidence remain available in Workbench.
          </p>
        )}
      </section>
      <section className="panel panel-body">
        <div className="lab-evidence-heading">
          <h2>Evidence & reproducibility</h2>
          <Button onClick={download}>Download replayable bundle</Button>
        </div>
        <p className="intro-copy">
          Replay recorded observations in the exact runner image. Hashes
          establish content identity, not correctness.
        </p>
        <details className="lab-disclosure">
          <summary>Technical provenance</summary>
          {[
            ["Source", report.source_hash],
            ["Tests", report.test_revision],
            ["Model", report.model.model_id],
            ["Runner", report.runner.digest],
          ].map(([key, value]) => (
            <p key={String(key)} className="hash">
              {String(key)}: {String(value || "Unavailable")}
            </p>
          ))}
        </details>
        <details className="lab-disclosure">
          <summary>
            Historical analogies · {report.precedents.length} eligible neighbors
          </summary>
          <p className="intro-copy">
            Train-only similarities are analogies, not output oracles.
          </p>
          {report.precedents.map((p, i) => (
            <details key={i}>
              <summary>
                Cosine {Number(p.similarity).toFixed(3)} ·{" "}
                {String(p.edit_summary)}
              </summary>
              <pre className="compact-json">{String(p.diff)}</pre>
              <p className="hash">
                {String(p.origin)} · {String(p.id)}
              </p>
            </details>
          ))}
        </details>
        <details className="lab-disclosure">
          <summary>Event timeline · {events.length} persisted events</summary>
          {events.map((e) => (
            <p className="timeline-entry" key={e.id}>
              <time>{e.timestamp}</time> · {e.stage} · {e.message}
            </p>
          ))}
          <details>
            <summary>Execution limits</summary>
            <pre className="compact-json">
              {JSON.stringify(report.limitations, null, 2)}
            </pre>
          </details>
        </details>
        {experiments.map(([title, key, action]) => {
          const data = report.intelligence[key] as
            | { status?: string; verification?: { status?: string } }
            | undefined;
          return (
            <details className="lab-disclosure" key={key}>
              <summary>
                {title} ·{" "}
                {data?.verification?.status ||
                  data?.status ||
                  "No recorded evidence"}
              </summary>
              {data ? (
                <IntelligencePanel
                  title={title}
                  data={data}
                  action={action && can(action) ? action : undefined}
                  report={report}
                  busy={busy}
                  run={run}
                  onSource={onSource}
                />
              ) : (
                <p className="intro-copy">
                  No eligible evidence or action for this report.
                </p>
              )}
            </details>
          );
        })}
      </section>
    </div>
  );
}
