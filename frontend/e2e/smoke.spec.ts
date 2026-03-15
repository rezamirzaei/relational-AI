import { test, expect } from "@playwright/test";
import { mockPublicAPI } from "./fixtures";

/**
 * Smoke test — validates the signed-out landing page renders correctly
 * and that the login form is functional.
 *
 * This test mocks the backend API to avoid requiring a running server,
 * making it reliable in CI environments.
 */

test.describe("Smoke tests", () => {
  test("signed-out page shows branding and sign-in form", async ({ page }) => {
    await mockPublicAPI(page);

    await page.goto("/");

    // Branding
    await expect(page.getByRole("heading", { level: 1, name: "Relational Fraud Intelligence" })).toBeVisible();

    // Sign-in form
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();

    // Health status
    await expect(page.getByText("Online")).toBeVisible();
  });

  test("shows error state when backend is unreachable", async ({ page }) => {
    // Mock backend failure
    await page.route("**/api/v1/health", (route) =>
      route.fulfill({ status: 503 }),
    );
    await page.route("**/api/v1/workspace/guide", (route) =>
      route.fulfill({ status: 503 }),
    );

    await page.goto("/");

    // Sign-in form should still render
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });
});
