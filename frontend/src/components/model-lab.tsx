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
    report.functions.find((f) => f.name === selected) || report.functions[0];
  const novelty = report.intelligence.novelty as
    | { status?: string; abstain?: boolean; reason?: string }
    | undefined;
  const metrics = report.model.metrics as
    | {
        test?: Record<
          string,
          { rf?: { n: number; f1: number }; xgb?: { n: number; f1: number } }
        >;
      }
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
        <h2>This analysis</h2>
        {fn ? (
          <>
            <label className="model-function">
              Selected function{" "}
              <select
                aria-label="Model function"
                value={fn.name}
                onChange={(e) => setSelected(e.target.value)}
              >
                {report.functions.map((f) => (
                  <option key={`${f.name}:${f.span.start_line}`} value={f.name}>
                    {f.name} · L{f.span.start_line}
                  </option>
                ))}
              </select>
            </label>
            <div className="model-analysis-summary">
              <div>
                <span className="label">ML risk estimate</span>
                <strong>{riskLabel(fn.risk)}</strong>
              </div>
              <div>
                <span className="label">Predicted family</span>
                <strong>{fn.family || "Unavailable"}</strong>
              </div>
              <div>
                <span className="label">Novelty / abstention</span>
                <strong>
                  {novelty?.abstain
                    ? "Abstaining on ML certainty"
                    : novelty?.status || "Unavailable"}
                </strong>
              </div>
            </div>
            <p className="intro-copy">
              Function AST features and train-fitted source TF-IDF inform the
              learned estimate. Static rules and coverage contribute separately
              to localization. Risk is not defect certainty; no per-feature
              model attribution is recorded.
            </p>
            <p className="intro-copy">
              Observed model inputs:{" "}
              {Object.entries(fn.features)
                .filter(([key]) =>
                  ["lines", "branches", "calls", "parameters"].includes(key),
                )
                .map(([key, value]) => `${key}: ${value}`)
                .join(" · ") || "Unavailable"}
              .
            </p>
            {novelty?.reason ? (
              <p className="intro-copy">{novelty.reason}</p>
            ) : null}
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
                    (report.localization.find((r) => r.function === fn.name)
                      ?.line as number) || fn.span.start_line,
                  )
                }
              >
                Explore in Fault Atlas
              </Button>
            </div>
          </>
        ) : (
          <p className="intro-copy">
            ML risk: Not applicable to script-only source. Script execution and
            static evidence remain available in Workbench.
          </p>
        )}
      </section>
      <section className="panel panel-body">
        <h2>Model reliability</h2>
        <p className="intro-copy">
          Small held-out cohorts. No measured ML localization uplift.
        </p>
        {metrics?.test ? (
          <div className="table-scroll">
            <table aria-label="Held-out comparison">
              <thead>
                <tr>
                  <th>Untouched cohort</th>
                  <th>RF · n / F1</th>
                  <th>XGBoost · n / F1</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(metrics.test).map(([name, c]) => (
                  <tr key={name}>
                    <td>{name.replaceAll("_", " ")}</td>
                    <td>
                      {c.rf
                        ? `${c.rf.n} / ${c.rf.f1.toFixed(3)}`
                        : "Unavailable"}
                    </td>
                    <td>
                      {c.xgb
                        ? `${c.xgb.n} / ${c.xgb.f1.toFixed(3)}`
                        : "Unavailable"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="intro-copy">
            Model evaluation is unavailable for this report.
          </p>
        )}
        <details className="lab-disclosure">
          <summary>Evaluation details</summary>
          <p className="intro-copy">
            Calibration: {String(report.model.calibration || "Unavailable")}
          </p>
          {metrics?.test ? (
            <ModelMetrics report={report} />
          ) : (
            <p className="intro-copy">
              RF/XGBoost evaluation artifacts were not included.
            </p>
          )}
          <details>
            <summary>Full cohort manifest and metrics</summary>
            <pre className="compact-json">
              {JSON.stringify(
                {
                  metrics: report.model.metrics,
                  cohorts: report.model.cohorts,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </details>
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
