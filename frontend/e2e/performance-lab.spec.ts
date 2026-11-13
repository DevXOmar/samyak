import { test, expect } from "@playwright/test";
test("real metrics-first lab, cohort comparisons, diagnostics and responsive evidence", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Boundary, not a guess/ }).click();
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  await expect(page.locator(".stage-clock")).toContainText("Active:");
  await expect(page.getByTestId("verdict")).toContainText("VALIDATED_ON_TESTS");
  await page.getByRole("tab", { name: "05 Model Lab & Vault" }).click();
  await expect(
    page.getByRole("heading", { name: "Model Performance", exact: true }),
  ).toBeVisible();
  const selector = page.getByLabel("Evaluation cohort");
  for (const cohort of ["REAL_BUGSINPY", "SYNTHETIC_ALGORITHM"]) {
    await selector.selectOption(cohort);
    await expect(page.getByLabel("pr_auc")).toContainText("XGBoost");
    await expect(page.getByLabel("Localization ablation")).toContainText("MRR");
    await expect(
      page.getByRole("table", { name: `${cohort} family confusion matrix` }),
    ).toBeVisible();
  }
  await page.getByRole("button", { name: /binary_search · L/ }).click();
  await page
    .getByText("Prediction diagnostics & static findings", { exact: true })
    .click();
  await expect(page.getByText(/Predicted family:/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Download replayable bundle" }),
  ).toBeEnabled();
  for (const width of [1440, 390])
    for (const theme of ["light", "dark"]) {
      await page.setViewportSize({ width, height: 1100 });
      const button = page.getByRole("button", {
        name: `Switch to ${theme} mode`,
      });
      if (await button.count()) await button.click();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      await page.screenshot({
        path: `test-results/performance-${width}-${theme}.png`,
        fullPage: true,
      });
    }
});

test("stalled SSE recovers actual completed evidence without resubmitting", async ({
  page,
}) => {
  let posts = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/v1/analyses")) posts++;
  });
  await page.route("**/events?after=*", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: ": transport stalled\n\n",
    }),
  );
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Python source editor" })
    .fill("def identity(value):\n    return value\n");
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  await expect(page.getByTestId("verdict")).toContainText(
    "INCONCLUSIVE_NO_OUTPUT_ORACLE",
  );
  expect(posts).toBe(1);
  await expect(
    page.getByRole("button", { name: "Analyze source", exact: true }),
  ).toBeEnabled();
});
