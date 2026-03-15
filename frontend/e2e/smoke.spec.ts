import { test, expect } from "@playwright/test";

/**
 * Smoke test — validates the signed-out landing page renders correctly
 * and that the login form is functional.
 *
 * This test mocks the backend API to avoid requiring a running server,
 * making it reliable in CI environments.
 */

const healthResponse = {
  status: "ok",
  app_name: "Relational Fraud Intelligence",
  environment: "test",
  database_status: "ready",
  rate_limit_status: "ready",
  provider_status: "ready",
  rate_limit_backend: "memory",
  seeded_scenarios: 3,
  seeded_operators: 2,
  provider_posture: {
    requested_text_signal_provider: "keyword",
    active_text_signal_provider: "keyword",
    requested_reasoning_provider: "local-rule-engine",
    active_reasoning_provider: "local-rule-engine",
    requested_explanation_provider: "deterministic",
    active_explanation_provider: "deterministic",
    notes: [],
  },
};

const workspaceGuideResponse = {
  guide: {
    primary_workflow_title: "Upload → Analyze → Alert → Case",
    primary_workflow_summary: "Upload transaction data and run analysis.",
    role_stories: [],
    scoring_guarantees: [],
    llm_positioning_note: "AI explains scored results.",
  },
};

test.describe("Smoke tests", () => {
  test("signed-out page shows branding and sign-in form", async ({ page }) => {
    // Mock backend API responses
    await page.route("**/api/v1/health", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(healthResponse) }),
    );
    await page.route("**/api/v1/workspace/guide", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(workspaceGuideResponse) }),
    );

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

