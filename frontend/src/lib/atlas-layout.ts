import dagre from "@dagrejs/dagre";
export type GraphNode = {
  id: string;
  kind: string;
  name?: string;
  target?: string;
  ast_type?: string;
  start_line?: number;
  end_line?: number;
  depth?: number;
  resolved?: boolean;
};
export type GraphEdge = {
  source: string;
  target: string;
  kind: string;
  variable?: string;
  resolved?: boolean;
};
export function layoutGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  horizontal = false,
) {
  const graph = new dagre.graphlib.Graph({ multigraph: true })
    .setGraph({
      rankdir: horizontal ? "LR" : "TB",
      nodesep: 55,
      ranksep: 85,
      marginx: 30,
      marginy: 30,
    })
    .setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => graph.setNode(n.id, { width: 220, height: 64 }));
  edges.forEach((e, i) => graph.setEdge(e.source, e.target, {}, String(i)));
  dagre.layout(graph);
  return nodes.map((n) => {
    const p = graph.node(n.id);
    return { ...n, position: { x: p.x - 110, y: p.y - 32 } };
  });
}
export const SIGNALS = [
  ["rule", "R", 0.4],
  ["model_risk", "M", 0.2],
  ["family_prior", "F", 0.15],
  ["graph_proximity", "G", 0.1],
  ["ochiai", "O", 0.35],
] as const;
export function contributions(signals: Record<string, unknown>) {
  return SIGNALS.map(([key, label, weight]) => ({
    key,
    label,
    weight,
    value: typeof signals[key] === "number" ? (signals[key] as number) : null,
    contribution:
      weight *
      (typeof signals[key] === "number" ? (signals[key] as number) : 0),
  }));
}
