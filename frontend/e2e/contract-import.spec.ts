import { test, expect } from "@playwright/test";
test("failure-first confirmation and witness evidence retain exact logical input", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Boundary, not a guess/ }).click();
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  await expect(page.getByTestId("verdict")).toContainText("VALIDATED_ON_TESTS");
  await page.getByRole("tab", { name: "03 Contract Studio" }).click();
  await expect(page.locator("table")).toHaveCount(0);
  await expect(page.getByText(/Passing \/ exploratory cases/)).toBeVisible();
  const failed = page.locator(".contract-case").first();
  await failed.locator("summary").first().click();
  await failed
    .getByRole("button", { name: "Reproduce / Find smaller witness" })
    .click();
  await expect(
    page.getByRole("button", { name: "Generate tests", exact: true }),
  ).toBeEnabled();
  await page
    .locator(".contract-case")
    .first()
    .locator("summary")
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Counterexample evidence" }),
  ).toContainText("INCONCLUSIVE_REDUCTION");
  await expect(
    page.getByRole("region", { name: "Counterexample evidence" }),
  ).not.toContainText("TypeError");
  await page.getByRole("button", { name: "Replay witness" }).click();
  await expect(
    page.getByRole("button", { name: "Generate tests", exact: true }),
  ).toBeEnabled();
});
test("GitHub selection clears fixtures and analyzes through real worker", async ({
  page,
}) => {
  const source = "def double(value):\n    return value * 2\n";
  const sha = "a".repeat(40);
  await page.route("**/api/v1/github/inspect", (r) =>
    r.fulfill({
      json: {
        repository: "demo/repository",
        url: "https://github.com/demo/repository",
        sha,
        partial: false,
        limits: "Deterministic GitHub fixture for transport testing",
        files: [
          {
            path: "src/double.py",
            size: source.length,
            functions: 1,
            reason: "Parsed self-contained Python",
            caveats: [],
          },
        ],
      },
    }),
  );
  await page.route("**/api/v1/github/file", (r) =>
    r.fulfill({
      json: {
        repository: "demo/repository",
        sha,
        path: "src/double.py",
        source,
        functions: 1,
        classes: 0,
        caveats: [],
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: /The caller trap/ }).click();
  await page
    .getByRole("button", { name: "Import from GitHub", exact: true })
    .click();
  await page
    .getByLabel("Public repository URL")
    .fill("https://github.com/demo/repository");
  await page
    .getByRole("button", { name: "Inspect repository", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Open in editor" }),
  ).toBeDisabled();
  await page
    .getByLabel(
      "Replace current source and clear its tests, stdin and evidence",
    )
    .check();
  await page.getByRole("button", { name: "Open in editor" }).click();
  await expect(
    page.getByRole("button", { name: "src/double.py" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /tests.json 0/ }),
  ).toBeVisible();
  const queued = page.waitForRequest(
    (r) => r.url().endsWith("/v1/analyses") && r.method() === "POST",
  );
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  const body = (await queued).postDataJSON();
  expect(body.tests).toEqual([]);
  expect(body.fixture).toBeNull();
  expect(body.stdin).toBe("");
  expect(body.provenance.path).toBe("src/double.py");
  await expect(
    page.getByRole("button", { name: "Analyze source", exact: true }),
  ).toBeEnabled();
  await expect(page.getByTestId("verdict")).toContainText("INCONCLUSIVE");
});

test("optional public GitHub connectivity import smoke", async ({ page }) => {
  test.skip(
    process.env.SAMYAK_GITHUB_SMOKE !== "1",
    "Set SAMYAK_GITHUB_SMOKE=1 for live public GitHub API connectivity",
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Import from GitHub", exact: true })
    .click();
  await page
    .getByLabel("Public repository URL")
    .fill("https://github.com/TheAlgorithms/Python");
  await page
    .getByRole("button", { name: "Inspect repository", exact: true })
    .click();
  await expect(page.locator(".github-files label").first()).toBeVisible();
  await page.getByRole("button", { name: "Open in editor" }).click();
  await expect(
    page
      .locator(".notice")
      .filter({ hasText: "Imported TheAlgorithms/Python" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Analyze source", exact: true }),
  ).toBeEnabled();
  await expect(page.getByTestId("verdict")).not.toContainText("AWAITING");
});
