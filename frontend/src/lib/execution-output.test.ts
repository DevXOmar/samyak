import { expect, it } from "vitest";
import { safeOutput } from "./execution-output";
it("retains real text and newlines without terminal clipboard, links or control commands", () => {
  expect(
    safeOutput("hello\n\x1b[31mred\x1b[0m\x1b]52;c;c2VjcmV0\x07\x00"),
  ).toBe("hello\nred");
  expect(
    safeOutput("\x1b]8;;https://example.com\x1b\\label\x1b]8;;\x1b\\"),
  ).toBe("label");
});
