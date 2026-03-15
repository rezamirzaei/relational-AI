import { test, expect } from "@playwright/test";
import { mockAuthenticatedAPI } from "./fixtures";

/**
 * Authentication workflow E2E tests.
 *
 * Verifies the login form submits successfully, the dashboard renders
 * after authentication, and subsequent API calls carry the Bearer token.
 */

test.describe("Authentication flow", () => {
  test("login form submits and transitions to dashboard", async ({ page }) => {
    await mockAuthenticatedAPI(page);
    await page.goto("/");

    // Fill in the sign-in form
    await page.getByLabel("Username").fill("analyst");
    await page.getByLabel("Password").fill("AnalystPassword123!");
    await page.getByRole("button", { name: "Sign in" }).click();

    // After login the operator display name or dashboard content should appear
    await expect(page.getByText("Fraud Analyst")).toBeVisible({ timeout: 10_000 });
  });

  test("authenticated requests include Bearer token", async ({ page }) => {
    await mockAuthenticatedAPI(page);

    // Intercept an authenticated API call and verify the header
    const tokenPromise = page.waitForRequest((req) =>
      req.url().includes("/api/v1/dashboard/stats") &&
      req.headers()["authorization"]?.startsWith("Bearer "),
    );

    await page.goto("/");
    await page.getByLabel("Username").fill("analyst");
    await page.getByLabel("Password").fill("AnalystPassword123!");
    await page.getByRole("button", { name: "Sign in" }).click();

    const request = await tokenPromise;
    expect(request.headers()["authorization"]).toBe("Bearer e2e-test-token");
  });
});

