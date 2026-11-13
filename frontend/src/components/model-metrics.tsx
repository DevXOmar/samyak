"use client";
import { useState } from "react";
import type { Report } from "@/lib/client";
export type MetricRow = {
  n: number;
  pr_auc: number | null;
  roc_auc: number | null;
  f1: number | null;
};
type Cohort = {
  rf?: MetricRow;
  xgb?: MetricRow;
  xgb_family?: {
    confusion_matrix: number[][];
    abstain_rate: number;
    excluded_unsupported: number;
  };
};
type Ablation = {
  n: number;
  top1: number | null;
  top3: number | null;
  mrr: number | null;
};
export function metricText(value: unknown) {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(3)
    : "N/A";
}
export function metricWidth(value: unknown) {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.max(0, Math.min(1, value)) * 100
    : 0;
}
export default function ModelMetrics({ report }: { report: Report }) {
  const metrics = report.model.metrics as
    | {
        test?: Record<string, Cohort>;
        localization_ablation?: Record<string, Record<string, Ablation>>;
      }
    | undefined;
  const names = Object.keys(metrics?.test || {});
  const [selection, setSelection] = useState("");
  const selected = names.includes(selection) ? selection : names[0];
  const cohort = metrics?.test?.[selected];
  const arms = metrics?.localization_ablation?.[selected] || {};
  const labels = report.model.families as string[] | undefined;
  const matrix = cohort?.xgb_family?.confusion_matrix;
  const max = Math.max(1, ...(matrix || []).flat());
  if (!cohort)
    return (
      <p className="intro-copy">
        Model evaluation is unavailable for this report.
      </p>
    );
  return (
    <>
      <div className="metric-cohort">
        <label>
          Held-out cohort{" "}
          <select
            aria-label="Evaluation cohort"
            value={selected}
            onChange={(e) => setSelection(e.target.value)}
          >
            {names.map((n) => (
              <option key={n} value={n}>
                {n === "REAL_BUGSINPY"
                  ? "BugsInPy"
                  : n === "SYNTHETIC_ALGORITHM"
                    ? "Algorithmic"
                    : n}
              </option>
            ))}
          </select>
        </label>
        <span className="muted">
          RF n={cohort.rf?.n ?? "N/A"} · XGBoost n={cohort.xgb?.n ?? "N/A"} ·
          separate untouched cohorts
        </span>
      </div>
      <div className="performance-metrics">
        {(["pr_auc", "roc_auc", "f1"] as const).map((key) => (
          <section key={key} aria-label={key}>
            <h3>
              {key === "pr_auc"
                ? "PR-AUC"
                : key === "roc_auc"
                  ? "ROC-AUC"
                  : "F1"}
            </h3>
            {(["rf", "xgb"] as const).map((head) => (
              <div className={`comparison-bar ${head}`} key={head}>
                <span>{head === "rf" ? "RF" : "XGBoost"}</span>
                <div className="metric-track">
                  <i
                    style={{ width: `${metricWidth(cohort[head]?.[key])}%` }}
                  />
                </div>
                <strong>{metricText(cohort[head]?.[key])}</strong>
              </div>
            ))}
          </section>
        ))}
      </div>
      <p className="metric-footnote">
        Held-out evaluation, not confidence in this submission. Small cohorts;
        N/A means the metric is undefined or absent. No measured ML localization
        uplift.
      </p>
      <details className="lab-disclosure" open>
        <summary>Localization · ML off / on</summary>
        {Object.keys(arms).length ? (
          <div className="table-scroll">
            <table aria-label="Localization ablation">
              <thead>
                <tr>
                  <th>Arm / evaluated n</th>
                  <th>Top-1</th>
                  <th>Top-3</th>
                  <th>MRR</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(arms).map(([name, row]) => (
                  <tr key={name}>
                    <th>
                      {name.replaceAll("_", " ")} · n={row.n}
                    </th>
                    {(["top1", "top3", "mrr"] as const).map((key) => (
                      <td key={key}>
                        <div className="ablation-cell">
                          <span className="metric-track">
                            <i style={{ width: `${metricWidth(row[key])}%` }} />
                          </span>
                          <code>{metricText(row[key])}</code>
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="intro-copy">
            No localization evaluation recorded for this cohort.
          </p>
        )}
      </details>
      <details className="lab-disclosure" open>
        <summary>Defect-family confusion matrix</summary>
        {matrix ? (
          <>
            <p className="metric-footnote">
              Counts · true labels down, predicted labels across. Hover cells
              for full labels. Excluded unsupported rows:{" "}
              {cohort.xgb_family?.excluded_unsupported ?? "N/A"}; abstention:{" "}
              {metricText(cohort.xgb_family?.abstain_rate)}.
            </p>
            <div className="table-scroll">
              <table
                className="confusion-heatmap"
                aria-label={`${selected} family confusion matrix`}
              >
                <thead>
                  <tr>
                    <th>True ↓ / predicted →</th>
                    {(labels || matrix.map((_, i) => String(i))).map(
                      (label) => (
                        <th key={label} title={label}>
                          {label
                            .split("_")
                            .map((s) => s[0])
                            .join("")}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {matrix.map((row, i) => (
                    <tr key={i}>
                      <th title={labels?.[i]}>
                        {(labels?.[i] || String(i)).replaceAll("_", " ")}
                      </th>
                      {row.map((n, j) => (
                        <td
                          key={j}
                          title={`${labels?.[i] || i} → ${labels?.[j] || j}: ${n}`}
                          style={{
                            background: `color-mix(in srgb, var(--gold) ${(n / max) * 55}%, var(--surface))`,
                          }}
                        >
                          {n}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="intro-copy">No family confusion matrix recorded.</p>
        )}
      </details>
      <details className="lab-disclosure">
        <summary>Evaluation details</summary>
        <p className="metric-footnote">
          Calibration: {String(report.model.calibration || "Unavailable")}.
          Model/index identities are available in Technical provenance.
        </p>
        <pre className="compact-json">
          {JSON.stringify(
            { metrics: report.model.metrics, cohorts: report.model.cohorts },
            null,
            2,
          )}
        </pre>
      </details>
    </>
  );
}
