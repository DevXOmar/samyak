"use client";
import type { Report } from "@/lib/client";
import { contributions } from "@/lib/atlas-layout";
export default function RankedSpans({
  report,
  line,
  onSelect,
}: {
  report: Report;
  line: number | null;
  onSelect: (n: number) => void;
}) {
  const row =
    report.localization.find((r) => r.line === line) || report.localization[0];
  const parts = contributions((row?.signals || {}) as Record<string, unknown>);
  const weighted = row && "rule" in (row.signals as Record<string, unknown>);
  return (
    <section className="panel panel-body">
      <h2>Ranked source spans</h2>
      <p className="intro-copy">
        Relative heuristic ranking, not probability or defect certainty.
      </p>
      <div className="rank-list">
        {report.localization.map((r, i) => {
          const strongest = contributions(
            r.signals as Record<string, unknown>,
          ).sort((a, b) => b.contribution - a.contribution)[0];
          return (
            <button
              key={`${String(r.function)}:${String(r.line)}:${i}`}
              aria-pressed={r === row}
              onClick={() => onSelect(Number(r.line))}
            >
              <strong>
                {i + 1}. {String(r.function)}:{String(r.line)}
              </strong>
              <code>{Number(r.score).toFixed(6)}</code>
              <span>
                {report.source.split("\n")[Number(r.line) - 1]?.trim()}
              </span>
              <small>
                {String(r.mode)} · strongest weighted signal: {strongest.key} (
                {strongest.contribution.toFixed(4)})
              </small>
            </button>
          );
        })}
      </div>
      {row ? (
        <div aria-label="Why this line?">
          <h3>
            Why this line? {String(row.function)}:{String(row.line)}
          </h3>
          {weighted ? (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>Actual value</th>
                    <th>Weight</th>
                    <th>Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {parts.map((p) => (
                    <tr key={p.key}>
                      <td>
                        {p.label} · {p.key}
                      </td>
                      <td>
                        {p.value == null
                          ? p.key === "ochiai"
                            ? "N/A (no eligible failing-test coverage)"
                            : "N/A"
                          : p.value.toFixed(6)}
                      </td>
                      <td>{p.weight.toFixed(2)}</td>
                      <td>{p.contribution.toFixed(6)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>
                Sum: {parts.reduce((s, p) => s + p.contribution, 0).toFixed(6)}{" "}
                · recorded score: {Number(row.score).toFixed(6)}
              </p>
              <details>
                <summary>Ranking formula</summary>
                <p>
                  S = 0.40R + 0.20M + 0.15F + 0.10G + 0.35O. Coefficients sum to
                  1.20. Missing Ochiai contributes zero. R: maximum matching
                  rule strength; M: containing function risk; F: family support;
                  G: graph proximity; O: failed_cover / sqrt(total_failed ×
                  (failed_cover + passed_cover)).
                </p>
              </details>
            </>
          ) : (
            <p>
              {String(row.mode)}: script observation/static strength; the
              function ranking formula does not apply.
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}
