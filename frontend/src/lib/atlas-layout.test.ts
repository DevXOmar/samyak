import { expect, it } from "vitest";
import { layoutGraph, contributions } from "./atlas-layout";
it("lays out cyclic and disconnected graphs deterministically without overlap", () => {
  const nodes = Array.from({ length: 100 }, (_, i) => ({
    id: String(i),
    kind: "Statement",
  }));
  const edges = nodes
    .slice(1)
    .map((n, i) => ({
      source: String(Math.floor(i / 2)),
      target: n.id,
      kind: "CONTROL_NEXT",
    }));
  edges.push({ source: "9", target: "0", kind: "TRUE_BRANCH" });
  for (const horizontal of [true, false]) {
    const placed = layoutGraph(nodes, edges, horizontal);
    expect(placed).toEqual(layoutGraph(nodes, edges, horizontal));
    for (const a of placed)
      for (const b of placed)
        if (a.id !== b.id)
          expect(
            Math.abs(a.position.x - b.position.x) >= 220 ||
              Math.abs(a.position.y - b.position.y) >= 64,
          ).toBe(true);
  }
});
it("reconstructs the unchanged score and contributes zero for missing coverage", () => {
  const p = contributions({
    rule: 0.8,
    model_risk: 0.6,
    family_prior: 0.2,
    graph_proximity: 0.5,
    ochiai: null,
  });
  expect(p.reduce((s, p) => s + p.contribution, 0)).toBeCloseTo(0.52);
  expect(p[4].value).toBeNull();
  expect(p.reduce((s, p) => s + p.weight, 0)).toBeCloseTo(1.2);
  expect(contributions({ ochiai: 1 })[4].contribution).toBe(0.35);
});
