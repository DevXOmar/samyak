import { describe, expect, it, vi, afterEach } from "vitest";
import {
  api,
  observed,
  observationLabel,
  observationTone,
  riskLabel,
  tone,
} from "./client";
import { sourceColumn } from "./utils";
describe("evidence presentation", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("does not replace unavailable predictions with fabricated numbers", () => {
    expect(riskLabel(null)).toBe("Unavailable");
    expect(riskLabel(0)).toBe("0.0%");
  });
  it("distinguishes inconclusive results from passing evidence", () => {
    expect(tone("INCONCLUSIVE_NO_OUTPUT_ORACLE")).toBe("warn");
    expect(tone("REJECTED_REGRESSION")).toBe("bad");
    expect(tone("VALIDATED_RUNTIME_FAULT_ONLY")).toBe("good");
    expect(observed(undefined)).toBe("Unrun");
  });
  it("never paints an output without an oracle as a correctness pass", () => {
    const result = {
      test_id: "x",
      status: "PASS",
      output: 7,
      lines: [],
      stdout: "",
      stderr: "",
      exit_code: null,
      duration_ms: null,
      traceback: null,
      fault_lines: [],
      samples_ms: [],
      median_ms: null,
      p95_ms: null,
      error: null,
      repeatable: true,
    };
    expect(observationLabel({ tier: "C", has_expected: false }, result)).toBe(
      "RETURNED_NO_ORACLE",
    );
    expect(observationTone({ has_expected: false }, result)).toBe("neutral");
    expect(observationLabel({ tier: "A", has_expected: true }, result)).toBe(
      "PASS",
    );
  });
  it("maps AST byte spans to exact Unicode editor columns", () => {
    expect(
      sourceColumn(
        "x = 'Ω' + nums[0]",
        1,
        new TextEncoder().encode("x = 'Ω' + ").length,
      ),
    ).toBe(11);
    expect(
      sourceColumn(
        "x = '😀' + nums[0]",
        1,
        new TextEncoder().encode("x = '😀' + ").length,
      ),
    ).toBe(12);
  });
  it("sends exact payloads and surfaces server failures", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "job" }), { status: 202 }),
      );
    vi.stubGlobal("fetch", fetcher);
    expect(await api("/v1/analyses", { source: "def f(): return 1" })).toEqual({
      id: "job",
    });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      source: "def f(): return 1",
    });
    fetcher.mockResolvedValue(new Response("not ready", { status: 409 }));
    await expect(api("/report")).rejects.toThrow("409: not ready");
  });
});
