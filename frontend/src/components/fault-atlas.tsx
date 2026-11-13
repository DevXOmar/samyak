"use client";
import { useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import type { Report } from "@/lib/client";
import { Badge } from "./ui/badge";
export default function FaultAtlas({
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
  const [mode, setMode] = useState("calls");
  const [scope, setScope] = useState("");
  const { nodes, edges } = useMemo(() => {
    const graph = ((mode === "ast"
      ? report.structure.syntax_tree
      : report.structure.graph) || { nodes: [], edges: [] }) as {
      nodes: {
        id: string;
        kind: string;
        name?: string;
        target?: string;
        resolved?: boolean;
        start_line?: number;
        ast_type?: string;
        depth?: number;
      }[];
      edges: {
        source: string;
        target: string;
        kind: string;
        resolved?: boolean;
        variable?: string;
      }[];
    };
    const selectedFunction = report.functions.find((f) => f.name === scope);
    const columns: Record<number, number> = {};
    const affected = new Set(
      Object.values(
        (
          report.intelligence.blast_radius as
            | { candidates?: Record<string, { affected_functions: string[] }> }
            | undefined
        )?.candidates || {},
      ).flatMap((c) => c.affected_functions),
    );
    const filtered = graph.nodes
      .filter(
        (n) =>
          !selectedFunction ||
          mode === "calls" ||
          (n.start_line != null &&
            n.start_line >= selectedFunction.span.start_line &&
            n.start_line <= selectedFunction.span.end_line),
      )
      .filter((n) =>
        mode === "calls"
          ? ["Function", "Call"].includes(n.kind) ||
            (n.kind === "Module" &&
              Number(
                (
                  report.structure.module as
                    | { statement_count?: number }
                    | undefined
                )?.statement_count || 0,
              ) > 0)
          : mode === "ast"
            ? true
            : n.kind === "Statement",
      )
      .slice(0, 65);
    const ids = new Set(filtered.map((n) => n.id));
    const nodes: Node[] = filtered.map((n, i) => ({
      id: n.id,
      position: {
        x:
          mode === "calls"
            ? n.kind === "Call"
              ? 320
              : 30
            : mode === "ast"
              ? (n.depth || 0) * 205
              : (i % 3) * 235,
        y:
          mode === "calls"
            ? i * 90
            : mode === "ast"
              ? ((columns[n.depth || 0] = (columns[n.depth || 0] || 0) + 1) -
                  1) *
                85
              : Math.floor(i / 3) * 100,
      },
      data: {
        label: `${n.name || n.target || n.ast_type || n.kind} ${n.start_line ? `: ${n.start_line}` : ""}${n.resolved === false ? " · unresolved" : ""}`,
        line: n.start_line,
      },
      selected: n.start_line === line,
      style: {
        width: 195,
        borderStyle: n.resolved === false ? "dashed" : "solid",
        borderColor: n.name && affected.has(n.name) ? "var(--gold)" : undefined,
      },
    }));
    const edges: Edge[] = graph.edges
      .filter(
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
      )
      .slice(0, 120)
      .map((e, i) => ({
        id: `${e.source}-${e.target}-${i}`,
        source: e.source,
        target: e.target,
        label: e.variable || e.kind.replaceAll("_", " "),
        style: { strokeDasharray: e.resolved === false ? "5 5" : undefined },
        labelStyle: { fill: "var(--muted)", fontSize: 9 },
        labelBgStyle: { fill: "var(--surface)" },
      }));
    return { nodes, edges };
  }, [report, mode, line, scope]);
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h2>Fault Atlas</h2>
          <p className="intro-copy">
            Select a node to inspect its source. Dashed edges remain unresolved.
          </p>
        </div>
        <div className="flex-row">
          {mode === "ast" ? (
            <select
              aria-label="Graph function"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              <option value="">All source</option>
              {report.functions.map((f) => (
                <option key={f.name} value={f.name}>
                  {f.name}
                </option>
              ))}
            </select>
          ) : null}
          <select
            aria-label="Graph view"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="calls">Call graph</option>
            <option value="ast">Python AST</option>
            <option value="defuse">Def-use</option>
            <option value="cfg">Control flow</option>
          </select>
        </div>
      </div>
      <div className="graph-canvas">
        <ReactFlow
          key={mode}
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{ maxZoom: 1 }}
          colorMode={dark ? "dark" : "light"}
          nodesConnectable={false}
          onNodeClick={(_, node) =>
            typeof node.data.line === "number" && onSelect(node.data.line)
          }
          aria-label="Interactive source graph"
        >
          <Background color="var(--border)" gap={22} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="editor-footer">
        <span>
          {nodes.length} visible nodes / {edges.length} edges · bounded to 65
          nodes
        </span>
        <Badge>Static approximation</Badge>
      </div>
    </div>
  );
}
