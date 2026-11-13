"use client";
import { ArrowRight, Play, RotateCcw, ShieldCheck } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { tone, type Report } from "@/lib/client";
type Row = Record<string, unknown>;
const obj = (value: unknown): Row =>
  value && typeof value === "object" ? (value as Row) : {};
const list = (value: unknown): Row[] =>
  Array.isArray(value) ? value.map(obj) : [];
const entries = (value: unknown) => Object.entries(obj(value));
const asText = (value: unknown) =>
  typeof value === "string" ? value : JSON.stringify(value);
const names: Record<string, string> = {
  witness: "Find smaller witness",
  precedents: "Compare retrieval",
  ledger: "Verify & replay",
  twin: "Run twin challenge",
  metamorphic: "Run Shield",
};
export default function IntelligencePanel({
  title,
  data,
  action,
  busy,
  run,
  report,
  onSource,
}: {
  title: string;
  data: unknown;
  action?: string;
  busy: boolean;
  run: (action: string, extra?: object) => void;
  report?: Report;
  onSource?: (line: number) => void;
}) {
  const row = obj(data);
  if (!data) return null;
  const candidateName = (id: string) => {
    const index = report?.candidates.findIndex((c) => c.id === id);
    return index != null && index >= 0
      ? `Candidate ${index + 1}`
      : id.slice(0, 12);
  };
  return (
    <section className="panel panel-body experiment" aria-label={title}>
      <header>
        <div className="flex-row">
          <ShieldCheck size={15} className="gold" />
          <h2>{title}</h2>
        </div>
        {action ? (
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => run(action)}
          >
            <Play size={11} />
            {names[action] || "Run experiment"}
          </Button>
        ) : null}
      </header>
      {row.status ? (
        <Badge
          tone={
            [
              "MEASURED",
              "REPRODUCED",
              "REPLAY_VERIFIED",
              "MATCH",
              "INTEGRITY_VERIFIED",
            ].includes(String(row.status))
              ? "good"
              : tone(String(row.status))
          }
        >
          {String(row.status)}
        </Badge>
      ) : null}
      {row.reason ? (
        <p className="muted text-xs mt-3">{String(row.reason)}</p>
      ) : null}
      {title === "Novelty Radar" ? (
        <>
          <div className="evidence-stats">
            <div>
              <span className="label">Nearest eligible cosine</span>
              <strong>
                {typeof row.nearest_similarity === "number"
                  ? row.nearest_similarity.toFixed(3)
                  : "Unavailable"}
              </strong>
            </div>
            <div>
              <span className="label">Conclusion</span>
              <strong>
                {row.abstain
                  ? "Abstain on ML certainty"
                  : "Familiar neighborhood"}
              </strong>
            </div>
            <div>
              <span className="label">Threshold basis</span>
              <strong>Explicitly heuristic</strong>
            </div>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Function</th>
                  <th>RF risk</th>
                  <th>XGB risk</th>
                  <th>Disagreement</th>
                  <th>Outlier features</th>
                </tr>
              </thead>
              <tbody>
                {list(row.functions).map((f) => (
                  <tr key={String(f.function)}>
                    <td>
                      <code>{String(f.function)}</code>
                    </td>
                    <td>{Number(f.rf_risk).toFixed(3)}</td>
                    <td>{Number(f.xgb_risk).toFixed(3)}</td>
                    <td>{Number(f.disagreement).toFixed(3)}</td>
                    <td>
                      {Array.isArray(f.outlier_features)
                        ? f.outlier_features.join(", ") || "None"
                        : "Unavailable"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted text-[10px] mt-3">
            Low similarity is unfamiliarity evidence. Static findings and
            runtime investigation continue.
          </p>
        </>
      ) : null}
      {title === "Counterexample Studio" && row.minimal_args ? (
        <>
          <div className="witness-comparison">
            <div>
              <span className="label">Original observed input</span>
              <code>{asText(row.original_args)}</code>
            </div>
            <ArrowRight size={16} className="gold" />
            <div>
              <span className="label">Smaller reproducible witness</span>
              <code>{asText(row.minimal_args)}</code>
            </div>
          </div>
          <div className="flex-row my-4">
            <Badge>{String(row.domain || "UNCONFIRMED")}</Badge>
            <Badge>{String(row.method)}</Badge>
          </div>
          <p className="mono text-xs">
            {String(
              row.failure_signature ||
                obj(row.result).error ||
                "Recorded runtime fault",
            )}
          </p>
          <div className="flex-row mt-4">
            {(Array.isArray(row.reached_lines)
              ? (row.reached_lines as number[])
              : []
            )
              .slice(0, 12)
              .map((line) => (
                <button
                  key={line}
                  className="chip"
                  onClick={() => onSource?.(line)}
                >
                  L{line}
                </button>
              ))}
            {obj(row.test).id ? (
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => run("replay", { test_id: obj(row.test).id })}
              >
                <RotateCcw size={12} />
                Replay minimized witness
              </Button>
            ) : null}
          </div>
        </>
      ) : null}
      {title === "Replay" && row.test ? (
        <div className="witness-comparison">
          <div>
            <span className="label">Exact input</span>
            <code>
              {String(obj(row.test).function)}({asText(obj(row.test).args)})
            </code>
          </div>
          <div>
            <span className="label">Observed replay</span>
            <code>
              {String(obj(row.result).status)} ·{" "}
              {asText(obj(row.result).error || obj(row.result).output)}
            </code>
          </div>
        </div>
      ) : null}
      {title === "Precedent comparison" ? (
        <>
          <div className="data-grid mt-4">
            <div>
              <span className="label">Smoothed operator distribution</span>
              {entries(row.operator_distribution).map(([key, value]) => (
                <div className="signal-row" key={key}>
                  <span style={{ minWidth: 170, fontSize: 9 }}>
                    {key.replaceAll("_", " ").toLowerCase()}
                  </span>
                  <div className="signal-bar">
                    <i style={{ width: `${Number(value) * 100}%` }} />
                  </div>
                  <code>{Number(value).toFixed(3)}</code>
                </div>
              ))}
            </div>
            <div>
              <span className="label">Recorded experiment</span>
              {obj(row.comparison).status === "MEASURED_ON_THIS_SUBMISSION" ? (
                <div className="table-scroll mt-3">
                  <table>
                    <thead>
                      <tr>
                        <th>Arm</th>
                        <th>First valid rank</th>
                        <th>Valid candidates</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entries(obj(row.comparison).arms).map(([key, arm]) => (
                        <tr key={key}>
                          <td>{key.replaceAll("_", " ")}</td>
                          <td>{String(obj(arm).first_valid_rank ?? "None")}</td>
                          <td>{String(obj(arm).validated_candidates)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="intro-copy">
                  Both orders execute the same frozen suite. No held-out
                  improvement is assumed.
                </p>
              )}
              <p className="hash mt-4">
                Index {String(row.index_id || "unavailable")}
              </p>
            </div>
          </div>
        </>
      ) : null}
      {title === "Blast radius" ? (
        <div className="data-grid mt-4">
          {entries(row.candidates).map(([id, value]) => (
            <div className="impact-card" key={id}>
              <div className="flex-row justify-between">
                <h3>{candidateName(id)}</h3>
                <Badge
                  tone={
                    Array.isArray(obj(value).caller_regression_ids) &&
                    (obj(value).caller_regression_ids as unknown[]).length
                      ? "bad"
                      : "neutral"
                  }
                >
                  {Array.isArray(obj(value).caller_regression_ids)
                    ? (obj(value).caller_regression_ids as unknown[]).length
                    : 0}{" "}
                  caller regressions
                </Badge>
              </div>
              <div className="flex-row mt-4">
                {(Array.isArray(obj(value).affected_functions)
                  ? (obj(value).affected_functions as string[])
                  : []
                ).map((fn) => (
                  <button
                    className="chip"
                    key={fn}
                    onClick={() => {
                      const f = report?.functions.find((f) => f.name === fn);
                      if (f) onSource?.(f.span.start_line);
                    }}
                  >
                    {fn}
                  </button>
                ))}
              </div>
              <p className="muted text-[10px] mt-3">
                {Array.isArray(obj(value).dependent_test_ids)
                  ? (obj(value).dependent_test_ids as unknown[]).length
                  : 0}{" "}
                dependent tests ·{" "}
                {Array.isArray(obj(value).unresolved_edges)
                  ? (obj(value).unresolved_edges as unknown[]).length
                  : 0}{" "}
                unresolved edges. Full available suites were run.
              </p>
            </div>
          ))}
        </div>
      ) : null}
      {title === "Repair Tournament" ? (
        <div className="table-scroll mt-4">
          <table>
            <thead>
              <tr>
                <th>Rank / candidate</th>
                <th>Elimination</th>
                <th>Fail → pass</th>
                <th>Pass → pass</th>
                <th>AST footprint</th>
              </tr>
            </thead>
            <tbody>
              {list(row.candidates).map((c, index) => (
                <tr key={String(c.candidate_id)}>
                  <td>
                    {index + 1} · {candidateName(String(c.candidate_id))}
                    {row.winner_id === c.candidate_id ? (
                      <Badge tone="good" className="ml-2">
                        WINNER
                      </Badge>
                    ) : null}
                  </td>
                  <td>
                    <Badge tone={tone(String(c.verdict))}>
                      {String(c.verdict)}
                    </Badge>
                  </td>
                  <td>{String(c.fail_to_pass)}</td>
                  <td>{String(c.pass_to_pass)}</td>
                  <td>{String(c.ast_edits ?? "Unavailable")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {title === "Repair Risk Budget" ? (
        <div className="data-grid mt-4">
          {entries(row.candidates).map(([id, value]) => (
            <div className="impact-card" key={id}>
              <div className="flex-row justify-between">
                <h3>{candidateName(id)}</h3>
                <Badge
                  tone={
                    obj(value).band === "DO_NOT_RECOMMEND"
                      ? "bad"
                      : obj(value).band === "AUTO_SUGGEST"
                        ? "good"
                        : "warn"
                  }
                >
                  {String(obj(value).band)}
                </Badge>
              </div>
              <ul className="muted text-xs mt-3 space-y-2">
                {(Array.isArray(obj(value).reasons)
                  ? (obj(value).reasons as string[])
                  : []
                ).map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
      {title === "Proof-Carrying Patch Ledger" ? (
        <>
          <div className="evidence-stats">
            <div>
              <span className="label">Source identity</span>
              <code>{String(row.source_hash).slice(0, 18)}…</code>
            </div>
            <div>
              <span className="label">Patch revisions</span>
              <strong>{entries(row.patch_hashes).length}</strong>
            </div>
            <div>
              <span className="label">Replay</span>
              <strong>{String(obj(row.verification).status)}</strong>
            </div>
          </div>
          {Array.isArray(obj(row.verification).replays) ? (
            <div className="flex-row mt-3">
              {list(obj(row.verification).replays).map((r) => (
                <span className="chip" key={String(r.revision)}>
                  <span className="mono">
                    {String(r.revision).slice(0, 14)}
                  </span>
                  <Badge tone={r.match ? "good" : "bad"}>
                    {r.match ? "MATCH" : "MISMATCH"}
                  </Badge>
                </span>
              ))}
            </div>
          ) : null}
          <p className="muted text-[10px] mt-3">
            Deterministic ZIP entries, fixed timestamps, SHA-256 files,
            model/index identity, exact runner digest and replay instructions.
          </p>
        </>
      ) : null}
      {title === "Semantic Twin Challenge" && row.status === "MEASURED" ? (
        <>
          <div className="evidence-stats">
            <div>
              <span className="label">Risk delta</span>
              <strong>{Number(row.risk_delta).toFixed(6)}</strong>
            </div>
            <div>
              <span className="label">Top-3 line overlap</span>
              <strong>{String(row.top3_overlap)}</strong>
            </div>
            <div>
              <span className="label">Twin repair verdict</span>
              <Badge tone={tone(String(row.twin_verdict))}>
                {String(row.twin_verdict)}
              </Badge>
            </div>
          </div>
          <details className="mt-4">
            <summary>Inspect the AST-identical source transform</summary>
            <pre>{String(row.source)}</pre>
          </details>
        </>
      ) : null}
      {title === "Metamorphic Shield" && row.status === "MEASURED" ? (
        <>
          <div className="evidence-stats">
            <div>
              <span className="label">Executed relations</span>
              <strong>{list(row.relations).length}</strong>
            </div>
            <div>
              <span className="label">Observed violations</span>
              <strong
                style={{
                  color: Number(row.violations)
                    ? "var(--error)"
                    : "var(--success)",
                }}
              >
                {String(row.violations)}
              </strong>
            </div>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Justified relation</th>
                  <th>Transformed input</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                {list(row.relations).map((r, i) => (
                  <tr key={i}>
                    <td>{String(r.relation).replaceAll("_", " ")}</td>
                    <td>
                      <code>{asText(obj(r.test).args)}</code>
                    </td>
                    <td>
                      <Badge tone={r.violated ? "bad" : "good"}>
                        {String(obj(r.result).status)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      <details className="mt-5">
        <summary>Inspect complete computation artifact</summary>
        <pre className="compact-json">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </section>
  );
}
