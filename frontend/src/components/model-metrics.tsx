import { Badge } from "./ui/badge";
import type { Report } from "@/lib/client";
type Binary = {
  n: number;
  pr_auc: number | null;
  roc_auc: number | null;
  f1: number;
};
type Family = {
  confusion_matrix: number[][];
  report: Record<string, { "f1-score"?: number; support?: number } | number>;
  abstain_rate: number;
  excluded_unsupported: number;
};
type Cohort = { rf?: Binary; xgb?: Binary; xgb_family?: Family };
const short = (name: string) =>
  name
    .split("_")
    .map((s) => s[0])
    .join("");
export default function ModelMetrics({ report }: { report: Report }) {
  const metrics = report.model.metrics as
    | {
        test?: Record<string, Cohort>;
        localization_ablation?: Record<
          string,
          Record<
            string,
            {
              n: number;
              top1: number | null;
              top3: number | null;
              mrr: number | null;
            }
          >
        >;
      }
    | undefined;
  const families = Array.isArray(report.model.families)
    ? (report.model.families as string[])
    : [];
  if (!metrics?.test)
    return (
      <p className="muted text-xs mt-4">
        Model evaluation is unavailable for this report.
      </p>
    );
  return (
    <>
      <div className="table-scroll mt-4">
        <table>
          <thead>
            <tr>
              <th>Untouched cohort / head</th>
              <th>n</th>
              <th>PR-AUC</th>
              <th>ROC-AUC</th>
              <th>F1</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(metrics.test).flatMap(([name, cohort]) =>
              (["rf", "xgb"] as const).map((head) => {
                const row = cohort[head];
                return row ? (
                  <tr key={name + head}>
                    <td>
                      {name.replaceAll("_", " ")}
                      <span className="label ml-2">{head.toUpperCase()}</span>
                    </td>
                    <td>{row.n}</td>
                    <td>{row.pr_auc?.toFixed(3) ?? "Unavailable"}</td>
                    <td>{row.roc_auc?.toFixed(3) ?? "Unavailable"}</td>
                    <td>{row.f1.toFixed(3)}</td>
                  </tr>
                ) : null;
              }),
            )}
          </tbody>
        </table>
      </div>
      <details className="mt-5">
        <summary>ML on / off localization ablation · measured holdout</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Cohort / arm</th>
                <th>n</th>
                <th>Top-1</th>
                <th>Top-3</th>
                <th>MRR</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics.localization_ablation || {}).flatMap(
                ([domain, arms]) =>
                  Object.entries(arms).map(([arm, row]) => (
                    <tr key={domain + arm}>
                      <td>
                        <span className="label">
                          {domain.replaceAll("_", " ")}
                        </span>
                        <p className="mono text-[10px] mt-1">{arm}</p>
                      </td>
                      <td>{row.n}</td>
                      <td>{row.top1?.toFixed(3) ?? "Unavailable"}</td>
                      <td>{row.top3?.toFixed(3) ?? "Unavailable"}</td>
                      <td>{row.mrr?.toFixed(3) ?? "Unavailable"}</td>
                    </tr>
                  )),
              )}
            </tbody>
          </table>
        </div>
        <p className="muted text-[10px] mt-3">
          Identical ranker signals and candidate budget, toggling learned
          priors. The current frozen cohort shows no uplift.
        </p>
      </details>
      <details className="mt-5">
        <summary>Defect-family confusion matrices</summary>
        {Object.entries(metrics.test).map(([domain, cohort]) =>
          cohort.xgb_family ? (
            <section key={domain} className="mt-5">
              <div className="flex-row justify-between">
                <span className="label">{domain.replaceAll("_", " ")}</span>
                <Badge>XGBOOST FAMILY HEAD</Badge>
              </div>
              <p className="muted text-[10px] mt-2">
                Rows: true labels. Columns: predicted labels. Excluded
                unsupported rows: {cohort.xgb_family.excluded_unsupported}.
                Abstention: {(cohort.xgb_family.abstain_rate * 100).toFixed(1)}
                %.
              </p>
              <div className="table-scroll mt-3">
                <table
                  className="matrix"
                  aria-label={`${domain} family confusion matrix`}
                >
                  <thead>
                    <tr>
                      <th>True ↓ / predicted →</th>
                      {families.map((name) => (
                        <th key={name} title={name}>
                          {short(name)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cohort.xgb_family.confusion_matrix.map((row, index) => (
                      <tr key={index}>
                        <th title={families[index]}>
                          {short(families[index] || String(index))}
                        </th>
                        {row.map((count, col) => (
                          <td key={col} className={count ? "nonzero" : "muted"}>
                            {count}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null,
        )}
        <p className="hash mt-3">
          {families
            .map((f) => `${short(f)} = ${f.replaceAll("_", " ")}`)
            .join(" · ")}
        </p>
      </details>
    </>
  );
}
