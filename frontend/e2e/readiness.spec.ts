import { test, expect } from "@playwright/test";
test("module-only input runs without fabricating function risk and live services stay separate", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Python source editor" })
    .fill('print("hello world")');
  await page
    .getByRole("button", { name: "Analyze source", exact: true })
    .click();
  await expect(
    page.getByText("ML risk: Not applicable to script-only source", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("status", { name: "Live service health" }),
  ).toContainText("Runner AVAILABLE");
  await expect(
    page.getByRole("button", { name: "Rerun analysis", exact: true }),
  ).toHaveCount(0);
});
