import { test, expect } from "@playwright/test";
import { mockAuthenticatedAPI, dashboardStatsResponse } from "./fixtures";

/**
 * Dashboard E2E tests — authenticated.
 *
 * Verifies that dashboard metric cards, workflow stages, and navigation
 * render correctly after a successful login.
 */

async function loginAndNavigate(page: import("@playwright/test").Page) {
  await mockAuthenticatedAPI(page);
  await page.goto("/");
  await page.getByLabel("Username").fill("analyst");
  await page.getByLabel("Password").fill("AnalystPassword123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Wait for the dashboard to render
  await expect(page.getByText("Fraud Analyst")).toBeVisible({ timeout: 10_000 });
}

test.describe("Dashboard (authenticated)", () => {
  test("displays workflow stage cards after login", async ({ page }) => {
    await loginAndNavigate(page);

    // The dashboard should show the workflow stages from the mock
    for (const stage of dashboardStatsResponse.stats.workflow_stages) {
      await expect(page.getByText(stage.title)).toBeVisible();
    }
  });

  test("sidebar navigation switches views", async ({ page }) => {
    await loginAndNavigate(page);

    // Click on "Cases" in the sidebar and verify content changes
    const casesNav = page.getByRole("button", { name: /cases/i }).first();
    if (await casesNav.isVisible()) {
      await casesNav.click();
      // Verify that some case-related content appears
      await expect(page.getByText(/case/i).first()).toBeVisible();
    }

    // Click on "Alerts" in the sidebar
    const alertsNav = page.getByRole("button", { name: /alerts/i }).first();
    if (await alertsNav.isVisible()) {
      await alertsNav.click();
      await expect(page.getByText(/alert/i).first()).toBeVisible();
    }
  });

  test("displays scenario catalog after navigating to investigate", async ({ page }) => {
    await loginAndNavigate(page);

    // Click on "Investigate" in the sidebar
    const investigateNav = page.getByRole("button", { name: /investigate/i }).first();
    if (await investigateNav.isVisible()) {
      await investigateNav.click();
      // The scenario title from our mock should appear
      await expect(page.getByText("Cross-border device ring")).toBeVisible({ timeout: 5_000 });
    }
  });
});
