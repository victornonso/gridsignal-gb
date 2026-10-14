import { test, expect } from "@playwright/test";
const screens = [
  ["overview", "The grid, in perspective."],
  ["carbon", "Understand the carbon signal."],
  ["generation", "Where the power comes from."],
  ["regional", "One grid. Different stories."],
  ["forecasts", "Measure the difference."],
  ["operations", "Trust starts at the source."],
  ["methodology", "Know what you’re measuring."],
];
for (const [screen, title] of screens) {
  test(`${screen}: real analytics and responsive layout`, async ({
    page,
  }, info) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`/?screen=${screen}&start=2026-10-07&end=2026-10-13`);
    await expect(
      page.getByRole("heading", { level: 1, name: title }),
    ).toBeVisible();
    await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 30000 });
    await expect(
      page.getByText(
        "Persisted analytics are temporarily unavailable. Please retry.",
        { exact: false },
      ),
    ).toHaveCount(0);
    if (screen !== "methodology")
      await expect(page.locator(".metric-value").first()).not.toHaveText("—");
    const dimensions = await page.evaluate(() => ({
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
    expect(errors).toEqual([]);
    await page.screenshot({
      path: `../../docs/screenshots/${screen}-${info.project.name}.png`,
      fullPage: true,
    });
  });
}
test("navigation, filters and CSV export", async ({ page }, info) => {
  await page.goto("/?screen=overview&start=2026-10-07&end=2026-10-13");
  if (info.project.name !== "desktop")
    await page
      .getByRole("button", { name: "Open navigation", exact: true })
      .click();
  await page
    .getByRole("button", { name: "Carbon analytics", exact: true })
    .click();
  await expect(page).toHaveURL(/screen=carbon/);
  await page.getByLabel("Geography", { exact: true }).selectOption("1");
  await expect(page).toHaveURL(/region=1/);
  await page.getByLabel("Resolution", { exact: true }).selectOption("hour");
  await expect(page).toHaveURL(/granularity=hour/);
  await page.getByLabel("From", { exact: true }).fill("2026-10-10");
  await expect(page).toHaveURL(/start=2026-10-10/);
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toBe("gridsignal-carbon.csv");
});
test("regional comparisons and operational drilldown", async ({ page }) => {
  await page.goto("/?screen=regional&start=2026-10-07&end=2026-10-13");
  await page.getByLabel("London", { exact: true }).check();
  await expect(page).toHaveURL(/13/);
  await page
    .locator(".table-scroll")
    .getByRole("button", { name: "Details →" })
    .first()
    .click();
  await expect(page).toHaveURL(/region=/);
  const today = new Date().toISOString().slice(0, 10);
  await page.goto(`/?screen=operations&start=${today}&end=${today}`);
  await page
    .locator(".table-scroll")
    .getByRole("button", { name: "Details →" })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("API outage is explicit and does not substitute data", async ({
  page,
}) => {
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Analytics temporarily unavailable" }),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert").first()).toContainText("unavailable", {
    timeout: 20000,
  });
  await expect(page.locator(".metric-value").first()).toHaveText("—");
});
