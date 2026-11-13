"use client";
import { useState } from "react";
import type { Report } from "@/lib/client";
import { observationLabel, observed } from "@/lib/client";
type Impact = {
  edited_function?: string;
  affected_functions?: string[];
  call_edges?: { source: string; target: string }[];
  def_use_edges?: unknown[];
  dependent_test_ids?: string[];
  caller_regression_ids?: string[];
  unresolved_edges?: { source: string; target: string }[];
  scope?: string;
};
export default function ImpactExplorer({
  report,
  index,
  onCandidate,
  onSource,
}: {
  report: Report;
  index: number;
  onCandidate: (n: number) => void;
  onSource: (n: number) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const c = report.candidates[index] || report.candidates[0];
  const all = report.intelligence.blast_radius as
    | { candidates?: Record<string, Impact> }
    | undefined;
  const impact = c ? all?.candidates?.[c.id] : undefined;
  // Top-level statements (e.g. an `if __name__ == "__main__":` block) are a real caller, not a function.
  const label = (id: string) => {
    const name = id.replace("fn:", "");
    return name === "module" ? "<module> top-level code" : name;
  };
  const callEdges = [
    ...new Map(
      (impact?.call_edges || []).map((e) => [`${e.source}>${e.target}`, e]),
    ).values(),
  ];
  const graphNodes =
    (
      report.structure.graph as
        | { nodes?: { id: string; target?: string }[] }
        | undefined
    )?.nodes || [];
  const unresolvedTargets = [
    ...new Set(
      (impact?.unresolved_edges || []).map(
        (e) => graphNodes.find((n) => n.id === e.target)?.target || e.target,
      ),
    ),
  ].sort();
  return (
    <section className="panel panel-body" aria-label="Blast radius">
      <h2>Blast radius</h2>
      <p className="intro-copy">
        Static reachability indicates potential impact, not confirmed changed
        behavior.
      </p>
      <select
        aria-label="Impact candidate"
        value={c?.id || ""}
        onChange={(e) =>
          onCandidate(
            report.candidates.findIndex((c) => c.id === e.target.value),
          )
        }
      >
        {report.candidates.map((c, i) => (
          <option key={c.id} value={c.id}>
            Candidate {i + 1} · {c.operator} · {c.verdict}
          </option>
        ))}
      </select>
      {c && impact ? (
        <>
          <h3 className="mt-4">What changed</h3>
          <button className="trace-link" onClick={() => onSource(c.line)}>
            {impact.edited_function || "Unknown function"} · L{c.line} ·{" "}
            {c.changed_lines} added/removed lines
          </button>
          <details>
            <summary>Exact patch footprint / diff</summary>
            <pre className="compact-json">{c.diff}</pre>
          </details>
          <h3 className="mt-4">Who could be affected</h3>
          {!callEdges.length ? (
            <p className="muted">
              No resolved callers in this source call the edited function.
            </p>
          ) : null}
          {callEdges.map((e, i) => {
            const caller = e.source.replace("fn:", ""),
              callee = e.target.replace("fn:", "");
            return (
              <p key={i}>
                <button
                  className="trace-link"
                  onClick={() =>
                    onSource(
                      report.functions.find((f) => f.name === caller)?.span
                        .start_line || c.line,
                    )
                  }
                >
                  {label(callee)} → {label(caller)} (
                  {callee === impact.edited_function
                    ? "direct caller"
                    : "transitive caller"}
                  )
                </button>
              </p>
            );
          })}
          <p>
            {impact.affected_functions?.map(label).join(" · ") ||
              "No resolved affected functions"}
          </p>
          <details>
            <summary>
              Relevant lexical def-use paths (
              {impact.def_use_edges?.length || 0})
            </summary>
            <pre className="compact-json">
              {JSON.stringify(impact.def_use_edges, null, 2)}
            </pre>
          </details>
          <h3 className="mt-4">Which tests checked it / what broke</h3>
          <p>
            {c.checks.filter((x) => x.regression).length} previously passing
            confirmed tests regressed;{" "}
            {impact.caller_regression_ids?.length || 0} caller regressions in
            callers of the edited function. None observed does not mean zero
            risk.
          </p>
          {impact.dependent_test_ids
            ?.slice()
            .sort(
              (a, b) =>
                Number(impact.caller_regression_ids?.includes(b)) -
                Number(impact.caller_regression_ids?.includes(a)),
            )
            .slice(0, showAll ? undefined : 3)
            .map((id) => {
              const t = report.tests.find((t) => t.id === id);
              const a = report.original_results.find((r) => r.test_id === id),
                b = c.results.find((r) => r.test_id === id);
              const regression = impact.caller_regression_ids?.includes(id);
              return (
                <details key={id} className="impact-test">
                  <summary>
                    {regression ? "CALLER REGRESSION · " : ""}
                    {t?.function || "Unknown test"} · {id} ·{" "}
                    {t ? observationLabel(t, a) : "UNKNOWN"} →{" "}
                    {t ? observationLabel(t, b) : "UNKNOWN"} ·{" "}
                    {a?.status === "PASS" && b?.status === "FAIL"
                      ? "pass-to-fail"
                      : a?.status === "PASS" && b?.status === "PASS"
                        ? "pass-to-pass"
                        : a &&
                            ["FAIL", "ERROR"].includes(a.status) &&
                            b?.status === "PASS"
                          ? "fail-to-pass"
                          : !b
                            ? "UNRUN"
                            : "inspect evidence"}
                  </summary>
                  <p>Original: {observed(a)}</p>
                  <p>Patched: {observed(b)}</p>
                  <pre className="compact-json">
                    {JSON.stringify(
                      {
                        input: t,
                        checks: c.checks.filter((x) => x.test_id === id),
                      },
                      null,
                      2,
                    )}
                  </pre>
                  <button
                    className="trace-link"
                    onClick={() =>
                      onSource(
                        report.functions.find((f) => f.name === t?.function)
                          ?.span.start_line || c.line,
                      )
                    }
                  >
                    Inspect caller source
                  </button>
                </details>
              );
            })}
          <button className="chip" onClick={() => setShowAll(!showAll)}>
            {showAll
              ? "Collapse test evidence"
              : `Inspect all ${impact.dependent_test_ids?.length || 0} dependent tests`}
          </button>
          <p className="mt-4">
            Candidate decision: {c.verdict}.{" "}
            {impact.caller_regression_ids?.length
              ? "Authoritative previously passing caller tests regressed; candidate rejected."
              : ""}
          </p>
          <h3>What is unknown</h3>
          <p>
            {impact.unresolved_edges?.length || 0} calls from affected code go
            to names not defined in this source
            {unresolvedTargets.length
              ? ` (${unresolvedTargets.slice(0, 8).join(", ")}${unresolvedTargets.length > 8 ? ", …" : ""})`
              : ""}
            ; their behavior is not traced. Bounded reverse traversal (32
            nodes); lexical def-use does not resolve aliasing. Untested paths
            remain unknown.
          </p>
          <details>
            <summary>Unresolved call edges</summary>
            <pre className="compact-json">
              {JSON.stringify(impact.unresolved_edges, null, 2)}
            </pre>
          </details>
        </>
      ) : (
        <p>NOT_SUPPORTED: no candidate impact evidence for this report.</p>
      )}
    </section>
  );
}
