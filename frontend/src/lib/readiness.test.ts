import { expect, it } from "vitest";
import { executionReadyToRerun } from "./readiness";
it("separates historical failure from live readiness without mutating history", () => {
  const report = Object.freeze({ status: "EXECUTION_UNAVAILABLE" });
  expect(executionReadyToRerun(report.status, "AVAILABLE", false)).toBe(true);
  expect(report.status).toBe("EXECUTION_UNAVAILABLE");
  expect(executionReadyToRerun(report.status, "AVAILABLE", true)).toBe(false);
  expect(
    executionReadyToRerun(report.status, "EXECUTION_UNAVAILABLE", false),
  ).toBe(false);
  expect(executionReadyToRerun("AVAILABLE", "AVAILABLE", false)).toBe(false);
});
