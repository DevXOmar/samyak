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
  nodeSize,
  type GraphNode,
  type GraphEdge,
} from "@/lib/atlas-layout";
import type { Report } from "@/lib/client";
// Fit the graph; one that cannot fit at a legible zoom (unless "All source (dense)") is shown
// from its entry (top for trees, left for flows) and can be panned/zoomed.
const READABLE_ZOOM = 0.5;
function Fit({
  identity,
  readable,
  horizontal,
}: {
  identity: string;
  readable: boolean;
  horizontal: boolean;
}) {
  const { fitView, getNodes, setViewport } = useReactFlow();
  const width = useStore((s) => s.width);
  const height = useStore((s) => s.height);
  useEffect(() => {
    const id = requestAnimationFrame(() => {
      // Layout sizes are explicit, so bounds do not depend on DOM measurement.
      const boxes = getNodes().map((n) => ({
        x: n.position.x,
        y: n.position.y,
        w: n.measured?.width ?? Number(n.style?.width ?? 0),
        h: n.measured?.height ?? Number(n.style?.height ?? 0),
      }));
      if (!boxes.length) return;
      const x0 = Math.min(...boxes.map((b) => b.x)),
        y0 = Math.min(...boxes.map((b) => b.y));
      const bounds = {
        x: x0,
        y: y0,
        width: Math.max(...boxes.map((b) => b.x + b.w)) - x0,
        height: Math.max(...boxes.map((b) => b.y + b.h)) - y0,
      };
      const fitted = Math.min(
        1,
        width / (bounds.width * 1.18 || 1),
        height / (bounds.height * 1.18 || 1),
      );
      if (!readable || fitted >= READABLE_ZOOM || !width) {
        void fitView({ padding: 0.18, maxZoom: 1 });
        return;
      }
      const zoom = READABLE_ZOOM;
      void setViewport({
        zoom,
        x: horizontal
          ? 24 - bounds.x * zoom
          : width / 2 - (bounds.x + bounds.width / 2) * zoom,
        y: horizontal
          ? height / 2 - (bounds.y + bounds.height / 2) * zoom
          : 24 - bounds.y * zoom,
      });
    });
    return () => cancelAnimationFrame(id);
  }, [
    identity,
    readable,
    horizontal,
    fitView,
    getNodes,
    setViewport,
    width,
    height,
  ]);
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
  const [initialFocus] = useState(() => report.functions[0]?.name);
  // The function holding the current selection; large graphs focus on it.
  const lineFn = report.functions.find(
    (f) => line != null && f.span.start_line <= line && line <= f.span.end_line,
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
  const modeNodes = useMemo(
    () =>
      (raw?.nodes || []).filter((n) =>
        mode === "calls"
          ? ["Function", "Call", "Module"].includes(n.kind)
          : mode === "ast" || n.kind === "Statement",
      ).length,
    [raw, mode],
  );
  // Whole-source graphs past these sizes cannot be read at a fitted zoom.
  const autoFn =
    !scope && modeNodes > (mode === "ast" ? 90 : 45)
      ? lineFn || report.functions.find((f) => f.name === initialFocus)
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
    let es = (raw?.edges || []).filter(
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
    // Call graph: one node per (caller, external target) instead of one per call site.
    let shown = visible,
      grouped = 0;
    if (mode === "calls") {
      const byId = new Map(visible.map((n) => [n.id, n]));
      const groups = new Map<string, GraphNode>();
      const remap = new Map<string, string>();
      for (const e of es) {
        const n = byId.get(e.target);
        if (n?.kind !== "Call") continue;
        const key = `ext:${e.source}:${n.target}`;
        remap.set(n.id, key);
        const g = groups.get(key);
        if (g) {
          g.count = (g.count || 1) + 1;
          g.start_line = Math.min(
            g.start_line ?? Infinity,
            n.start_line ?? Infinity,
          );
        } else groups.set(key, { ...n, id: key, count: 1 });
      }
      shown = [...visible.filter((n) => !remap.has(n.id)), ...groups.values()];
      const seen = new Set<string>();
      const before = es.length;
      es = es
        .map((e) => ({ ...e, target: remap.get(e.target) ?? e.target }))
        .filter((e) => {
          const k = `${e.source}>${e.target}`;
          if (seen.has(k)) return false;
          seen.add(k);
          return true;
        });
      grouped = before - es.length;
    }
    return {
      ns: layoutGraph(
        shown,
        es,
        mode === "calls" || mode === "defuse",
        mode === "ast",
      ),
      es,
      grouped,
      omitted: ns.length - visible.length,
      omittedEdges:
        (raw?.edges || []).filter(
          (e) => eligible.has(e.source) && eligible.has(e.target),
        ).length -
        es.length -
        grouped,
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
        >{`${n.kind === "Module" ? "<module>" : n.name || n.target || n.ast_type || n.kind}${(n.count || 1) > 1 ? ` ×${n.count}` : ""}${n.start_line ? ` : ${n.start_line}` : ""}`}</span>
      ),
      line: n.start_line,
    },
    selected: n.start_line === line || n.id === selected,
    style: {
      ...nodeSize(mode === "ast"),
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
            {autoFn
              ? `Auto · large graph, focused on ${autoFn.name}`
              : "All source"}
          </option>
          {modeNodes > (mode === "ast" ? 90 : 45) ? (
            <option value="__all__">All source (dense)</option>
          ) : null}
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
            identity={`${mode}:${scope}:${depth}:${external}:${focus?.name || ""}`}
            readable={scope !== "__all__"}
            horizontal={mode === "calls" || mode === "defuse"}
          />
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <p className="execution-message">
        {nodes.length} nodes · {edges.length} edges · {base.omitted} nodes /{" "}
        {base.omittedEdges} non-visible or other-mode edges omitted.{" "}
        {focus
          ? `Showing ${focus.name} only (${modeNodes} nodes in the whole source). `
          : ""}
        {base.grouped
          ? `${base.grouped} repeated call sites grouped (×n). `
          : ""}
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
