import { it, expect } from "vitest";
import { metricText, metricWidth } from "../components/model-metrics";
import { stageDurations } from "../components/stage-clock";
it("keeps zero separate from unavailable metrics and bounds visual bars", () => {
  expect(metricText(null)).toBe("N/A");
  expect(metricText(0)).toBe("0.000");
  expect(metricText(NaN)).toBe("N/A");
  expect(metricWidth(0)).toBe(0);
  expect(metricWidth(0.8)).toBe(80);
});
it("uses actual persisted timestamps for stage durations", () => {
  const events = [
    {
      id: 1,
      job_id: "j",
      stage: "structure",
      timestamp: "2026-01-01T00:00:00Z",
      message: "",
    },
    {
      id: 2,
      job_id: "j",
      stage: "prediction",
      timestamp: "2026-01-01T00:00:02.500Z",
      message: "",
    },
  ];
  expect(stageDurations(events)).toEqual([
    { stage: "structure", seconds: 2.5 },
  ]);
});
