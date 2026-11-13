import { test, expect, type Page } from "@playwright/test";
async function load(page: Page, fixture: string) {
  await page.getByRole("button", { name: fixture }).click();
  await expect(
    page.getByRole("button", { name: "Analyze source", exact: true }),
  ).toBeEnabled();
}
async function analyze(page: Page) {
  const queued = page.waitForResponse(
    (r) => r.url().endsWith("/v1/analyses") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  const response = await queued;
  expect(response.status()).toBe(202);
  await expect(
    page.getByRole("button", { name: "Analyze source", exact: true }),
  ).toBeEnabled();
  await expect(page.getByTestId("verdict")).not.toContainText("AWAITING");
  return (await response.json()).id as string;
}
async function workspace(page: Page, name: string) {
  await page.getByRole("tab", { name, exact: false }).click();
}
test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A clearer view of what could break." }),
  ).toBeVisible();
});

test("editing, live analysis, exact findings, graph, accepted/rejected diffs and stale evidence", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await load(page, "Boundary, not a guess");
  const editor = page.getByRole("textbox", { name: "Python source editor" });
  await expect(editor).toBeVisible();
  await editor.focus();
  await page.keyboard.press(
    process.platform === "darwin" ? "Meta+ArrowDown" : "Control+End",
  );
  await page.keyboard.type("\n# fresh edited submission");
  await analyze(page);
  await expect(page.getByTestId("verdict")).toContainText("VALIDATED_ON_TESTS");
  await page.getByRole("button", { name: /L3 · binary_search/ }).click();
  await expect(page.locator(".evidence-rail")).toContainText("loop off by one");
  await workspace(page, "Fault Atlas");
  await expect(page.locator(".react-flow__node").first()).toBeVisible();
  await page.getByLabel("Graph view").selectOption("ast");
  await expect(page.locator(".react-flow__node").first()).toBeVisible();
  await workspace(page, "Repair Arena");
  await page
    .getByRole("button", { name: /CANDIDATE.*VALIDATED_ON_TESTS/i })
    .click();
  await expect(
    page.getByRole("heading", { name: "Why this repair survives" }),
  ).toBeVisible();
  await expect(page.locator(".monaco-diff-editor")).toBeVisible();
  await expect(
    page.locator(".monaco-diff-editor .editor.original"),
  ).toBeVisible();
  await expect(
    page.locator(".monaco-diff-editor .editor.modified"),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Repair Tournament" }),
  ).toContainText("WINNER");
  await workspace(page, "Workbench");
  await editor.focus();
  await page.keyboard.press(
    process.platform === "darwin" ? "Meta+ArrowDown" : "Control+End",
  );
  await page.keyboard.type("\n# stale now");
  await expect(
    page.getByRole("status").filter({ hasText: "Source changed" }),
  ).toContainText("Source changed");
  await expect(page.getByTestId("verdict")).toContainText("AWAITING ANALYSIS");
  expect(errors).toEqual([]);
});

test("spec-less crash, exact domain confirmation, No and Yes oracle revisions", async ({
  page,
}) => {
  await load(page, "An unknown contract");
  await analyze(page);
  await expect(page.getByTestId("verdict")).toContainText(
    "INCONCLUSIVE_NO_OUTPUT_ORACLE",
  );
  await workspace(page, "Contract Studio");
  const empty = page
    .locator(".contract-case")
    .filter({ hasText: "average([[]])" })
    .first();
  await expect(empty).toContainText("ZeroDivisionError");
  const domain = page.waitForResponse((r) =>
    r.url().endsWith("/contracts/domain"),
  );
  await empty
    .getByRole("button", { name: "Confirm domain", exact: true })
    .click();
  expect((await domain).status()).toBe(202);
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  await expect(page.locator(".intro-action")).toContainText("COMPLETED");
  await workspace(page, "Workbench");
  await expect(page.getByTestId("verdict")).toContainText(
    "VALIDATED_RUNTIME_FAULT_ONLY",
  );
  await workspace(page, "Contract Studio");
  const row = page
    .locator(".contract-case")
    .filter({ hasText: "average([[]])" })
    .first();
  await row.locator("summary").first().click();
  const no = page.waitForResponse((r) =>
    r.url().endsWith("/contracts/decision"),
  );
  await row
    .getByRole("button", { name: "Reject proposed expectation", exact: true })
    .click();
  expect((await no).status()).toBe(202);
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  const current = page
    .locator(".contract-case")
    .filter({ hasText: "average([[]])" })
    .first();
  await current.locator("summary").first().click();
  await current
    .getByRole("button", { name: "Edit expected", exact: true })
    .click();
  await page.getByLabel("Expected output / JSON").fill("0");
  await page.getByRole("button", { name: "Confirm & rerun" }).click();
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  await workspace(page, "Workbench");
  await expect(page.getByTestId("verdict")).toContainText("VALIDATED_ON_TESTS");
});

test("caller trap, blast radius, policy and ledger controls expose real evidence", async ({
  page,
}) => {
  await load(page, "The caller trap");
  await analyze(page);
  await workspace(page, "Repair Arena");
  await page
    .getByRole("button", {
      name: /CANDIDATE.*replace return.*REJECTED_REGRESSION/i,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Why this repair does not win" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Repair Risk Budget" }),
  ).toContainText("DO_NOT_RECOMMEND");
  await workspace(page, "Fault Atlas");
  await expect(
    page.getByRole("region", { name: "Blast radius" }),
  ).toContainText("contains");
  await expect(
    page.getByRole("region", { name: "Blast radius" }),
  ).toContainText(/caller regressions/);
  await workspace(page, "Model Lab & Vault");
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Novelty Radar" })
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Novelty Radar" }),
  ).toContainText("Explicitly heuristic");
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download replayable bundle" })
    .click();
  expect((await download).suggestedFilename()).toContain("samyak");
});

test("unfamiliar correct fixture abstains without false confirmation", async ({
  page,
}) => {
  await load(page, "Correct, but suspicious");
  await analyze(page);
  await expect(page.getByTestId("verdict")).toContainText(
    "INCONCLUSIVE_NO_OUTPUT_ORACLE",
  );
  await expect(page.locator(".finding-list")).toContainText("bad condition");
  await workspace(page, "Model Lab & Vault");
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Novelty Radar" })
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Novelty Radar" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Held-out evaluation, not confidence in this submission. Small cohorts; N/A means the metric is undefined or absent. No measured ML localization uplift.",
    ),
  ).toBeVisible();
});

test("390px and 1440px layouts, theme persistence, fullscreen and keyboard controls", async ({
  page,
}) => {
  for (const width of [390, 1440, 1920]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(
      page.getByRole("button", { name: "Fullscreen editor", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await page
    .getByRole("button", { name: "Fullscreen editor", exact: true })
    .click();
  await expect(page.locator(".editor-fullscreen")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".editor-fullscreen")).toHaveCount(0);
});

test("SSE transport reconnects without fabricated progress or lost reports", async ({
  page,
}) => {
  let interrupted = false;
  await page.route("**/events?after=*", async (route) => {
    if (!interrupted) {
      interrupted = true;
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("textbox", { name: "Python source editor" })
    .fill("def identity(value):\n    return value\n");
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Connection interrupted" }),
  ).toContainText("Connection interrupted");
  await expect(
    page.getByRole("button", { name: "Analyze source", exact: true }),
  ).toBeEnabled();
  await expect(page.getByTestId("verdict")).toContainText(
    "INCONCLUSIVE_NO_OUTPUT_ORACLE",
  );
  await expect(page.getByText("PERSISTED", { exact: true })).toBeVisible();
  expect(interrupted).toBe(true);
});

test("witness, retrieval, twin and ledger actions produce inspected artifacts", async ({
  page,
}) => {
  await load(page, "Boundary, not a guess");
  await analyze(page);
  await workspace(page, "Contract Studio");
  await page
    .locator(".contract-case")
    .first()
    .locator("summary")
    .first()
    .click();
  await page
    .getByRole("button", { name: "Reproduce / Find smaller witness" })
    .click();
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  await page
    .locator(".contract-case")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Counterexample evidence" }),
  ).toContainText("REPRODUCED");
  await page.getByRole("button", { name: "Replay witness" }).click();
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  await expect(
    page
      .locator(".case-details details")
      .filter({ hasText: "Replay evidence" })
      .first(),
  ).toContainText("MATCH");
  await workspace(page, "Repair Arena");
  await page.getByRole("button", { name: "Compare retrieval" }).click();
  await expect(
    page.getByRole("button", { name: "Compare retrieval" }),
  ).toBeEnabled();
  await expect(
    page.getByRole("region", { name: "Precedent comparison" }),
  ).toContainText("First valid rank");
  await workspace(page, "Model Lab & Vault");
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Semantic Twin Challenge" })
    .locator("summary")
    .first()
    .click();
  const pendingRuntwinchallenge = page.waitForResponse(
    (r) => r.url().endsWith("/investigate") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run twin challenge" }).click();
  const newRuntwinchallenge = await (await pendingRuntwinchallenge).json();
  await expect(page.locator(".intro-action")).toContainText(
    newRuntwinchallenge.id.slice(0, 8),
  );
  await expect(page.locator(".intro-action")).toContainText("COMPLETED");
  await expect(
    page.getByRole("heading", { name: "Code Intelligence", exact: true }),
  ).toBeVisible();
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Semantic Twin Challenge" })
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Run twin challenge" }),
  ).toBeEnabled();
  await expect(
    page.getByRole("region", { name: "Semantic Twin Challenge" }),
  ).toContainText("MEASURED");
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Proof-Carrying Patch Ledger" })
    .locator("summary")
    .first()
    .click();
  const pendingVerifyreplay = page.waitForResponse(
    (r) => r.url().endsWith("/investigate") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Verify & replay" }).click();
  const newVerifyreplay = await (await pendingVerifyreplay).json();
  await expect(page.locator(".intro-action")).toContainText(
    newVerifyreplay.id.slice(0, 8),
  );
  await expect(page.locator(".intro-action")).toContainText("COMPLETED");
  await expect(
    page.getByRole("heading", { name: "Code Intelligence", exact: true }),
  ).toBeVisible();
  await page
    .locator(".lab-disclosure")
    .filter({ hasText: "Proof-Carrying Patch Ledger" })
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Verify & replay" }),
  ).toBeEnabled();
  await expect(
    page.getByRole("region", { name: "Proof-Carrying Patch Ledger" }),
  ).toContainText("REPLAY_VERIFIED");
});

test("explicit property contract enables the real Metamorphic Shield", async ({
  page,
}) => {
  const editor = page.getByRole("textbox", { name: "Python source editor" });
  await editor.focus();
  await page.keyboard.type("def normalize(nums):\n    return nums\n");
  await analyze(page);
  await workspace(page, "Contract Studio");
  await page.getByText("Advanced property checks", { exact: true }).click();
  await page
    .getByRole("button", { name: "Declare sorting contract: normalize" })
    .click();
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  await page.getByText("Advanced property checks", { exact: true }).click();
  await page.getByRole("button", { name: "Run Shield" }).click();
  await expect(
    page.getByRole("button", { name: "Generate tests" }),
  ).toBeEnabled();
  await page.getByText("Advanced property checks", { exact: true }).click();
  await expect(page.getByRole("button", { name: "Run Shield" })).toBeEnabled();
  const shield = page.getByRole("region", { name: "Metamorphic Shield" });
  await expect(shield).toContainText("MEASURED");
  await expect(shield).toContainText("FAIL");
  await expect(shield).toContainText("idempotence");
});
