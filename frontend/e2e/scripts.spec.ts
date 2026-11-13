import { test, expect, type Page } from "@playwright/test";
async function execute(page: Page, source: string, mode = "Run", stdin = "") {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Python source editor" })
    .fill(source);
  if (stdin) {
    await page.locator(".script-input summary").click();
    await page.getByLabel("Script standard input").fill(stdin);
  }
  const queued = page.waitForResponse(
    (r) => r.url().endsWith("/v1/analyses") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: mode, exact: true }).click();
  const response = await queued;
  expect(response.status()).toBe(202);
  const id = (await response.json()).id;
  await expect(
    page.getByRole("button", { name: "Run", exact: true }),
  ).toBeEnabled();
  const report = await (
    await page.request.get(`/api/v1/analyses/${id}/report`)
  ).json();
  return report;
}
for (const [name, source, expected, status] of [
  [
    "hello",
    'print("Hello, Samyak!")',
    "Hello, Samyak!\n",
    "EXECUTED_SUCCESSFULLY",
  ],
  [
    "loop",
    "for i in range(3):\n    print(i)",
    "0\n1\n2\n",
    "EXECUTED_SUCCESSFULLY",
  ],
  [
    "main guard",
    'if __name__ == "__main__":\n    print("main")',
    "main\n",
    "EXECUTED_SUCCESSFULLY",
  ],
  ["NameError", 'helloworld("Print")', "", "ERROR"],
  ["division by zero", "print(1 / 0)", "", "ERROR"],
  ["timeout", "while True:\n    pass", "", "TIMEOUT"],
]) {
  test(`isolated script: ${name}`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const report = await execute(page, source);
    expect(report.script_result.status).toBe(status);
    expect(report.script_result.stdout).toBe(expected);
    expect(report.overall_risk).toBeNull();
    expect(report.candidates).toEqual([]);
    await expect(page.getByTestId("verdict")).toContainText(status);
    await expect(page.getByTestId("execution-output-text")).toHaveText(
      expected,
    );
    await expect(
      page.getByText("ML risk: Not applicable to script-only source", {
        exact: true,
      }),
    ).toBeVisible();
    if (status === "ERROR") {
      await page
        .getByRole("tab", { name: "Execution Trace", exact: true })
        .click();
      await expect(page.locator(".execution-trace")).toContainText(
        name === "NameError" ? "NameError" : "ZeroDivisionError",
      );
      await page
        .getByRole("button", { name: /submission.py:1 — jump/ })
        .click();
      await expect(
        page.locator(".monaco-editor .selected-text").first(),
      ).toBeVisible();
      await page.getByRole("tab", { name: /Problems/ }).click();
      await expect(page.locator(".execution-problem").last()).toContainText(
        "OBSERVED_RUNTIME_FAULT",
      );
    }
    if (name === "hello") {
      await page.getByRole("tab", { name: "02 Fault Atlas" }).click();
      await expect(
        page.locator(".react-flow__node").filter({ hasText: "Module" }),
      ).toBeVisible();
      await expect(page.locator(".react-flow__edge")).toHaveCount(1);
      await page.getByLabel("Graph view").selectOption("cfg");
      await expect(page.locator(".react-flow__node").first()).toBeVisible();
    }
    expect(errors).toEqual([]);
  });
}

test("stdin, analysis, dismissal, clear and source edits preserve honest evidence", async ({
  page,
}) => {
  const report = await execute(
    page,
    'print(input("Name: "))',
    "Analyze source",
    "Samyak\n",
  );
  expect(report.script_result.stdout).toBe("Name: Samyak\n");
  await page.getByRole("button", { name: "Dismiss script suggestion" }).click();
  await page.getByRole("tab", { name: "Execution Trace", exact: true }).click();
  await expect(page.locator(".execution-trace")).toContainText(
    "domain unconfirmed",
  );
  await page.getByRole("tab", { name: "Output", exact: true }).click();
  await expect(
    page.getByText("Your script is running.", { exact: false }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Clear output view" }).click();
  await expect(page.getByTestId("execution-output-text")).toHaveText("");
  expect(
    (
      await (
        await page.request.get(`/api/v1/analyses/${report.job_id}/report`)
      ).json()
    ).script_result.stdout,
  ).toBe("Name: Samyak\n");
  await page.getByLabel("Script standard input").fill("Different\n");
  await expect(page.getByTestId("verdict")).toContainText("AWAITING ANALYSIS");
  await expect(page.locator(".execution-panel")).toContainText("invalidated");
  const editor = page.getByRole("textbox", { name: "Python source editor" });
  await editor.focus();
  await editor.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await page.keyboard.insertText('print("fresh")');
  await editor.press(
    process.platform === "darwin" ? "Meta+Enter" : "Control+Enter",
  );
  await expect(page.getByTestId("execution-output-text")).toHaveText("fresh\n");
  await editor.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await page.keyboard.insertText('print("edited again")');
  await expect(page.getByTestId("execution-output-text")).toHaveText("");
});

test("script output fits mobile and desktop themes, resizing and fullscreen", async ({
  page,
}) => {
  await execute(page, 'print("readable output")');
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Execution panel height").focus();
  await page.keyboard.press("End");
  await expect(page.getByLabel("Execution panel height")).toHaveValue("450");
  await page
    .getByRole("button", { name: "Fullscreen editor", exact: true })
    .click();
  await expect(
    page.locator(".editor-fullscreen .execution-terminal"),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/script-dark.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await page.screenshot({
    path: "test-results/script-light.png",
    fullPage: true,
  });
});

test("C printf receives a Python language explanation and a real NameError", async ({
  page,
}) => {
  const report = await execute(page, 'printf("hello")');
  expect(report.script_result.error).toContain("NameError");
  await expect(page.locator(".execution-panel")).toContainText(
    "printf is a C library function",
  );
});
