import { test, expect } from "@playwright/test";
let id: string;
let report: Record<string, unknown>;
test.beforeAll(async ({ request }) => {
  const job = await (
    await request.post("/api/v1/analyses", {
      data: { source: "def identity(value):\n    return value\n" },
    })
  ).json();
  id = job.id;
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/v1/analyses/${id}`)).json()).status,
      { timeout: 180000 },
    )
    .toBe("COMPLETED");
  report = await (await request.get(`/api/v1/analyses/${id}/report`)).json();
});
test("restore does not run; dismissal survives reload and rerun is optional", async ({
  page,
}) => {
  let posts = 0,
    reads = 0;
  page.on("request", (r) => {
    if (r.method() === "POST") posts++;
    if (r.url().endsWith(`/analyses/${id}/report`)) reads++;
  });
  await page.addInitScript(
    (value) => localStorage.setItem("samyak-job-v1", value),
    id,
  );
  await page.route(`**/analyses/${id}/report`, (r) =>
    r.fulfill({
      json: { ...report, runner: { status: "EXECUTION_UNAVAILABLE" } },
    }),
  );
  await page.goto("/");
  const notice = page.locator(".historical-inline");
  await expect(notice).toContainText("Previous analysis ran without execution");
  expect(posts).toBe(0);
  expect(reads).toBe(1);
  await expect(
    page.getByRole("status", { name: "Live service health" }),
  ).toContainText("AVAILABLE");
  await page.getByLabel("Dismiss previous execution notice").click();
  await page.reload();
  await expect(page.getByTestId("verdict")).not.toContainText("AWAITING");
  await expect(notice).toHaveCount(0);
  expect(posts).toBe(0);
  await page.evaluate(
    (value) => localStorage.removeItem(`samyak-rerun-dismissed:${value}`),
    id,
  );
  await page.reload();
  await expect(notice).toBeVisible();
  await notice.getByRole("button", { name: "Rerun", exact: true }).click();
  await expect(notice).toHaveCount(0);
  expect(posts).toBe(1);
});
test("model lab uses real metrics, retains actions and fits both themes", async ({
  page,
}) => {
  await page.addInitScript(
    (value) => localStorage.setItem("samyak-job-v1", value),
    id,
  );
  await page.goto("/");
  await expect(page.getByTestId("verdict")).not.toContainText("AWAITING");
  await page.getByRole("tab", { name: "05 Model Lab & Vault" }).click();
  await expect(
    page.getByRole("heading", { name: "This analysis", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Held-out comparison")).toBeVisible();
  await expect(
    page.getByText(
      "Small held-out cohorts. No measured ML localization uplift.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run twin challenge" }),
  ).toBeHidden();
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Semantic Twin Challenge" })
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Run twin challenge" }),
  ).toBeVisible();
  for (const width of [1440, 390])
    for (const theme of ["light", "dark"]) {
      await page.setViewportSize({ width, height: 1000 });
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
        path: `test-results/model-${width}-${theme}.png`,
        fullPage: true,
      });
    }
});
test("missing model and script-only evidence are explained", async ({
  page,
}) => {
  await page.addInitScript(
    (value) => localStorage.setItem("samyak-job-v1", value),
    id,
  );
  await page.route(`**/analyses/${id}/report`, (r) =>
    r.fulfill({
      json: { ...report, functions: [], model: {}, intelligence: {} },
    }),
  );
  await page.goto("/");
  await expect(page.getByTestId("verdict")).not.toContainText("AWAITING");
  await page.getByRole("tab", { name: "05 Model Lab & Vault" }).click();
  await expect(
    page.getByRole("heading", { name: "This analysis", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Not applicable to script-only source/),
  ).toBeVisible();
  await expect(
    page.getByText("Model evaluation is unavailable for this report.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Download replayable bundle" }),
  ).toBeEnabled();
});
