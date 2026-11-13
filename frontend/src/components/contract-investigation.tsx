"use client";
import type { Report } from "@/lib/client";
import { observationLabel, observationTone, observed } from "@/lib/client";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import IntelligencePanel from "./intelligence-panel";
export default function ContractInvestigation({
  report,
  busy,
  run,
  confirm,
  proposal,
  accept,
  onSource,
}: {
  report: Report;
  busy: boolean;
  run: (path: string, body: object) => void;
  confirm: (id: string) => void;
  proposal: (id: string) => Report["original_results"][number] | null;
  accept: (id: string, value: unknown) => void;
  onSource: (line: number) => void;
}) {
  const original = new Map(report.original_results.map((r) => [r.test_id, r]));
  const failing = report.tests.filter(
    (t) => original.get(t.id)?.status !== "PASS",
  );
  const rest = report.tests.filter((t) => !failing.includes(t));
  const invoke = (action: string, extra = {}) =>
    run(`/v1/analyses/${report.job_id}/investigate`, { action, ...extra });
  const witness = report.intelligence.witness as
    | {
        parent_test_id?: string;
        test_id?: string;
        test?: { id?: string };
        original_args?: unknown;
        minimal_args?: unknown;
        result?: unknown;
        status?: string;
        reduction_status?: string;
        reason?: string;
        reached_lines?: number[];
      }
    | undefined;
  function row(t: Report["tests"][number]) {
    const r = original.get(t.id);
    const proposed = !t.has_expected ? proposal(t.id) : null;
    const failed = ["FAIL", "ERROR"].includes(r?.status || "");
    const unresolved = !r || !["PASS", "FAIL", "ERROR"].includes(r.status);
    return (
      <article className="contract-case" key={t.id}>
        <details>
          <summary>
            <code>
              {t.function}({JSON.stringify(t.args)})
            </code>
            <Badge tone={observationTone(t, r)}>{observationLabel(t, r)}</Badge>
            <p className="contract-outcome">
              {r?.status === "FAIL" && t.has_expected
                ? `${JSON.stringify(t.expected)} → ${JSON.stringify(r.output)}`
                : observed(r)}
            </p>
          </summary>
          <div className="case-details">
            <p>{t.reason}</p>
            <p>
              Oracle {t.tier} · domain {t.domain} · {t.origin}
            </p>
            {t.has_expected ? (
              <p>
                Expected: <code>{JSON.stringify(t.expected)}</code>
              </p>
            ) : t.property ? (
              <p>
                Expected property: {t.property} (explicitly declared B oracle).
              </p>
            ) : (
              <p>
                No exact output oracle. A returned value alone does not
                establish correctness.
              </p>
            )}
            <p>Actual: {observed(r)}</p>
            <p className="hash">Test {t.id}</p>
            <div className="flex-row">
              {r?.lines.map((at) => (
                <button className="chip" key={at} onClick={() => onSource(at)}>
                  L{at}
                </button>
              ))}
            </div>
            <div className="flex-row mt-3">
              <Button
                disabled={busy}
                variant="outline"
                size="sm"
                onClick={() => invoke("replay", { test_id: t.id })}
              >
                Replay
              </Button>
              <Button
                disabled={busy}
                variant="outline"
                size="sm"
                onClick={() => confirm(t.id)}
              >
                Edit expected
              </Button>
              {t.domain !== "CONFIRMED" ? (
                <Button
                  disabled={busy}
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    run(`/v1/analyses/${report.job_id}/contracts/domain`, {
                      test_ids: [t.id],
                      reviewer: "workbench-user",
                    })
                  }
                >
                  Confirm input domain
                </Button>
              ) : null}
              {failed ? (
                <Button
                  disabled={busy}
                  size="sm"
                  variant="ghost"
                  onClick={() => invoke("witness", { test_id: t.id })}
                >
                  Reproduce / Find smaller witness
                </Button>
              ) : null}
            </div>
            {proposed ? (
              <div className="notice mt-3">
                Unverified repair proposal:{" "}
                <code>{JSON.stringify(proposed.output)}</code>
                <div className="flex-row">
                  <Button
                    disabled={busy}
                    size="sm"
                    variant="outline"
                    onClick={() => accept(t.id, proposed.output)}
                  >
                    Yes, expect {JSON.stringify(proposed.output)}
                  </Button>
                  <Button
                    disabled={busy}
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      run(`/v1/analyses/${report.job_id}/contracts/decision`, {
                        test_id: t.id,
                        expected: proposed.output,
                        reviewer: "workbench-user",
                      })
                    }
                  >
                    Reject proposed expectation
                  </Button>
                </div>
              </div>
            ) : null}
            {witness &&
            (witness.parent_test_id === t.id || witness.test_id === t.id) ? (
              <section aria-label="Counterexample evidence">
                <h3>Smaller reproducible witness</h3>
                <p>
                  {witness.status} · {witness.reduction_status} ·{" "}
                  {witness.reason}
                </p>
                <pre className="compact-json">
                  {JSON.stringify(witness.original_args)} →{" "}
                  {JSON.stringify(witness.minimal_args)}
                </pre>
                <details>
                  <summary>Matching failure evidence</summary>
                  <pre className="compact-json">
                    {JSON.stringify(witness.result, null, 2)}
                  </pre>
                </details>
                {witness.test?.id ? (
                  <Button
                    disabled={busy}
                    size="sm"
                    onClick={() =>
                      invoke("replay", { test_id: witness.test?.id })
                    }
                  >
                    Replay witness
                  </Button>
                ) : null}
              </section>
            ) : null}
            {report.intelligence.replay ? (
              <details>
                <summary>Replay evidence</summary>
                <pre className="compact-json">
                  {JSON.stringify(report.intelligence.replay, null, 2)}
                </pre>
              </details>
            ) : null}
            <details>
              <summary>Complete case evidence</summary>
              <pre className="compact-json">
                {JSON.stringify({ test: t, result: r }, null, 2)}
              </pre>
            </details>
          </div>
        </details>
        <Button
          disabled={busy}
          size="sm"
          variant="outline"
          onClick={() =>
            unresolved
              ? invoke("replay", { test_id: t.id })
              : failed
                ? t.domain !== "CONFIRMED"
                  ? run(`/v1/analyses/${report.job_id}/contracts/domain`, {
                      test_ids: [t.id],
                      reviewer: "workbench-user",
                    })
                  : invoke("replay", { test_id: t.id })
                : confirm(t.id)
          }
        >
          {unresolved
            ? "Replay"
            : failed
              ? t.domain !== "CONFIRMED"
                ? "Confirm domain"
                : "Reproduce"
              : "Confirm expected"}
        </Button>
      </article>
    );
  }
  const eligible = report.inference.filter(
    (f) =>
      Array.isArray(f.parameters) &&
      f.parameters.length === 1 &&
      ((f.parameters[0] as { candidate_type?: string }).candidate_type ===
        "list[int]" ||
        (f.parameters[0] as { evidence_source?: string }).evidence_source ===
          "AST_OPERATIONS_NUMERIC_FALLBACK"),
  );
  const declared = report.tests.some((t) => t.property === "sorted_multiset");
  return (
    <>
      <div className="page-intro">
        <div>
          <h2>Test investigation</h2>
          <p className="intro-copy">
            {
              failing.filter((t) =>
                ["FAIL", "ERROR"].includes(original.get(t.id)?.status || ""),
              ).length
            }{" "}
            failed ·{" "}
            {report.original_results.filter((r) => r.status === "PASS").length}{" "}
            returned/passed ·{" "}
            {
              report.tests.filter(
                (t) =>
                  !original.has(t.id) ||
                  !["PASS", "FAIL", "ERROR"].includes(
                    original.get(t.id)!.status,
                  ),
              ).length
            }{" "}
            unresolved ·{" "}
            {report.tests.filter((t) => t.domain === "UNCONFIRMED").length}{" "}
            unconfirmed
          </p>
        </div>
        <Button
          disabled={busy}
          variant="outline"
          onClick={() => run(`/v1/analyses/${report.job_id}/tests`, {})}
        >
          Generate tests
        </Button>
      </div>
      <section className="panel panel-body">
        <h3>Failures / needs investigation</h3>
        {failing.length ? (
          failing.map(row)
        ) : (
          <p className="intro-copy">
            No failing cases observed. This does not prove correctness.
          </p>
        )}
        <details className="mt-4">
          <summary>Passing / exploratory cases ({rest.length})</summary>
          {rest.map(row)}
        </details>
      </section>
      <details className="panel panel-body mt-4">
        <summary>Input inference</summary>
        <pre className="compact-json">
          {JSON.stringify(report.inference, null, 2)}
        </pre>
        <p>
          A: exact expected behavior · B: justified property · I: in-contract
          runtime fault · C: exploration. Domains remain independent.
        </p>
      </details>
      {eligible.length || declared ? (
        <details className="panel panel-body mt-4">
          <summary>Advanced property checks</summary>
          <p>
            Optional explicit contract: ascending sort of one finite integer
            list, preserving its multiset. No contract is assumed.
          </p>
          {eligible.map((f) => (
            <Button
              key={String(f.function)}
              disabled={busy}
              size="sm"
              variant="outline"
              onClick={() =>
                run(`/v1/analyses/${report.job_id}/contracts/property`, {
                  function: f.function,
                  property: "sorted_multiset",
                  reviewer: "workbench-user",
                })
              }
            >
              Declare sorting contract: {String(f.function)}
            </Button>
          ))}
          {declared ? (
            <IntelligencePanel
              title="Metamorphic Shield"
              report={report}
              data={report.intelligence.metamorphic}
              action="metamorphic"
              busy={busy}
              run={invoke}
            />
          ) : null}
        </details>
      ) : null}
    </>
  );
}
