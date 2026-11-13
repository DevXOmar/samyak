"use client";
import { useMemo, useState, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Position,
  useReactFlow,
  useStore,
  ReactFlowProvider,
} from "@xyflow/react";
import {
  layoutGraph,
  type GraphNode,
  type GraphEdge,
} from "@/lib/atlas-layout";
import type { Report } from "@/lib/client";
function Fit({ identity }: { identity: string }) {
  const { fitView } = useReactFlow();
  const width = useStore((s) => s.width);
  const height = useStore((s) => s.height);
  useEffect(() => {
    const id = requestAnimationFrame(
      () => void fitView({ padding: 0.18, maxZoom: 1 }),
    );
    return () => cancelAnimationFrame(id);
  }, [identity, fitView, width, height]);
  return null;
}
export default function Atlas(props: {
  report: Report;
  onSelect: (line: number) => void;
  line: number | null;
  dark: boolean;
}) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  );
}
function Graph({
  report,
  onSelect,
  line,
  dark,
}: {
  report: Report;
  onSelect: (line: number) => void;
  line: number | null;
  dark: boolean;
}) {
  const [initialFocus] = useState(
    () =>
      report.functions.find(
        (f) =>
          line != null && f.span.start_line <= line && line <= f.span.end_line,
      )?.name || report.functions[0]?.name,
  );
  const [mode, setMode] = useState("calls");
  const [scope, setScope] = useState("");
  const [external, setExternal] = useState(true);
  const [depth, setDepth] = useState(4);
  const [variable, setVariable] = useState("");
  const [selected, setSelected] = useState("");
  const raw = (
    mode === "ast" ? report.structure.syntax_tree : report.structure.graph
  ) as { nodes: GraphNode[]; edges: GraphEdge[] } | undefined;
  const fn = report.functions.find((f) => f.name === scope);
  const autoFn =
    mode === "ast" && !scope && (raw?.nodes.length || 0) > 90
      ? report.functions.find((f) => f.name === initialFocus)
      : undefined;
  const focus = fn || autoFn;
  const base = useMemo(() => {
    let ns = (raw?.nodes || []).filter((n) =>
      mode === "calls"
        ? (["Function", "Call"].includes(n.kind) ||
            (n.kind === "Module" &&
              raw?.edges.some(
                (e) => e.kind === "CALLS" && e.source === n.id,
              ))) &&
          (external || n.resolved !== false)
        : mode === "ast" || n.kind === "Statement",
    );
    if (focus)
      ns = ns.filter((n) =>
        mode === "calls"
          ? n.id === `fn:${focus.name}` ||
            (raw?.edges || []).some(
              (e) =>
                e.kind === "CALLS" &&
                (e.source === `fn:${focus.name}` ||
                  e.target === `fn:${focus.name}`) &&
                (e.source === n.id || e.target === n.id),
            )
          : n.start_line != null &&
            n.start_line >= focus.span.start_line &&
            (n.end_line || n.start_line) <= focus.span.end_line,
      );
    const eligible = new Set(ns.map((n) => n.id));
    const rootDepth = Math.min(...ns.map((n) => n.depth || 0));
    const visible =
      mode === "ast"
        ? ns.filter((n) => (n.depth || 0) <= rootDepth + depth)
        : ns;
    const ids = new Set(visible.map((n) => n.id));
    const es = (raw?.edges || []).filter(
      (e) =>
        ids.has(e.source) &&
        ids.has(e.target) &&
        (mode === "calls"
          ? e.kind === "CALLS"
          : mode === "ast"
            ? true
            : mode === "defuse"
              ? e.kind === "DEF_USE"
              : ["CONTROL_NEXT", "TRUE_BRANCH", "FALSE_BRANCH"].includes(
                  e.kind,
                )),
    );
    return {
      ns: layoutGraph(visible, es, mode === "calls" || mode === "defuse"),
      es,
      omitted: ns.length - visible.length,
      omittedEdges:
        (raw?.edges || []).filter(
          (e) => eligible.has(e.source) && eligible.has(e.target),
        ).length - es.length,
    };
  }, [raw, mode, external, focus, depth]);
  const nodes = base.ns.map((n) => ({
    id: n.id,
    position: n.position,
    sourcePosition:
      mode === "calls" || mode === "defuse" ? Position.Right : Position.Bottom,
    targetPosition:
      mode === "calls" || mode === "defuse" ? Position.Left : Position.Top,
    data: {
      label: (
        <span
          className="atlas-node-label"
          title={JSON.stringify(n)}
        >{`${n.name || n.target || n.ast_type || n.kind}${n.start_line ? ` : ${n.start_line}` : ""}`}</span>
      ),
      line: n.start_line,
    },
    selected: n.start_line === line || n.id === selected,
    style: {
      width: 220,
      height: 64,
      borderRadius: n.kind === "Function" ? 18 : 5,
      borderStyle: n.resolved === false ? "dashed" : "solid",
      borderColor: n.start_line === line ? "var(--gold)" : undefined,
    },
    ariaLabel: JSON.stringify(n),
  }));
  const edges = base.es.map((e, i) => ({
    id: String(i),
    ...e,
    type: "smoothstep",
    label:
      mode === "cfg" && e.kind !== "CONTROL_NEXT"
        ? e.kind.replace("_BRANCH", "")
        : mode === "defuse"
          ? e.variable
          : undefined,
    style: {
      stroke:
        e.kind === "TRUE_BRANCH"
          ? "var(--success)"
          : e.kind === "FALSE_BRANCH"
            ? "var(--warning)"
            : variable && e.variable === variable
              ? "var(--gold)"
              : undefined,
      strokeWidth: variable && e.variable === variable ? 3 : 1,
      strokeDasharray: e.resolved === false ? "5 5" : undefined,
    },
    selected:
      base.ns.some(
        (n) =>
          n.start_line === line && (n.id === e.source || n.id === e.target),
      ) ||
      (line == null && (e.source === selected || e.target === selected)),
    labelStyle: { fontSize: 10, fill: "var(--ink)" },
    labelBgStyle: { fill: "var(--surface)" },
  }));
  return (
    <section className="panel">
      <div className="panel-heading atlas-controls">
        <h2>Fault Atlas</h2>
        <select
          aria-label="Graph function"
          value={scope}
          onChange={(e) => setScope(e.target.value)}
        >
          <option value="">
            All source
            {autoFn ? " (large AST focuses first/selected function)" : ""}
          </option>
          {report.functions.map((f) => (
            <option key={f.name}>{f.name}</option>
          ))}
        </select>
        <select
          aria-label="Graph view"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="calls">Call graph</option>
          <option value="ast">Python AST</option>
          <option value="cfg">Control flow</option>
          <option value="defuse">Def-use</option>
        </select>
        {mode === "calls" ? (
          <label>
            <input
              type="checkbox"
              checked={external}
              onChange={(e) => setExternal(e.target.checked)}
            />{" "}
            External calls
          </label>
        ) : null}
        {mode === "ast" ? (
          <button onClick={() => setDepth((d) => d + 2)}>
            Expand branches (+2 levels)
          </button>
        ) : null}
        {mode === "defuse" ? (
          <select
            aria-label="Highlight variable"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
          >
            <option value="">All variables</option>
            {[...new Set(base.es.map((e) => e.variable).filter(Boolean))].map(
              (v) => (
                <option key={v}>{v}</option>
              ),
            )}
          </select>
        ) : null}
      </div>
      <div className="graph-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          colorMode={dark ? "dark" : "light"}
          nodesConnectable={false}
          nodesDraggable={false}
          minZoom={0.03}
          onNodeClick={(_, n) => {
            setSelected(n.id);
            if (typeof n.data.line === "number") onSelect(n.data.line);
          }}
        >
          <Fit
            identity={`${mode}:${scope}:${depth}:${external}:${autoFn?.name || ""}`}
          />
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <p className="execution-message">
        {nodes.length} nodes · {edges.length} edges · {base.omitted} nodes /{" "}
        {base.omittedEdges} non-visible or other-mode edges omitted.{" "}
        {Boolean(
          (report.structure.syntax_tree as { truncated?: boolean })?.truncated,
        ) && mode === "ast"
          ? "Backend AST artifact is truncated at its recorded limit. "
          : ""}
        Solid: resolved · dashed: unresolved · green/amber: true/false · gold:
        selected dependency. Static approximation.
      </p>
      <details className="panel-body">
        <summary>Selected node / edge details</summary>
        <pre className="compact-json">
          {JSON.stringify(
            {
              node: raw?.nodes.find((n) => n.id === selected),
              edges: base.es.filter(
                (e) => e.source === selected || e.target === selected,
              ),
            },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
