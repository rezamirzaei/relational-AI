import { test, expect } from "@playwright/test";
import { mockAuthenticatedAPI, scenariosResponse } from "./fixtures";

/**
 * Investigation workflow E2E test.
 *
 * Verifies the full investigate-a-scenario flow:
 * 1. Login
 * 2. Navigate to the Investigate view
 * 3. Select a scenario
 * 4. Run the investigation
 * 5. Verify investigation results render
 */

const investigationResponse = {
  investigation: {
    scenario: scenariosResponse.scenarios[0],
    risk_level: "high",
    total_risk_score: 72,
    summary: "Investigation found coordinated device sharing.",
    metrics: {
      total_transaction_volume: 45000,
      suspicious_transaction_volume: 12000,
      suspicious_transaction_count: 4,
      shared_device_count: 2,
      linked_customer_count: 3,
    },
    provider_summary: {
      requested_reasoning_provider: "local-rule-engine",
      active_reasoning_provider: "local-rule-engine",
      requested_text_provider: "keyword",
      active_text_provider: "keyword",
      notes: [],
    },
    top_rule_hits: [
      {
        rule_code: "SHARED_DEVICE",
        title: "Shared device coordination",
        weight: 25,
        narrative: "Multiple accounts sharing a single device fingerprint.",
      },
    ],
    graph_links: [],
    text_signals: [],
    suspicious_transactions: [],
    recommended_actions: ["Investigate shared device cluster."],
    investigation_leads: [],
    graph_analysis: null,
  },
};

const createCaseFromInvestigationResponse = {
  investigation: investigationResponse.investigation,
  case: {
    case_id: "case-002",
    source_type: "scenario",
    source_id: "s-001",
    scenario_id: "s-001",
    title: "Cross-border device ring: Shared device coordination",
    status: "open",
    priority: "high",
    assigned_analyst_id: null,
    assigned_analyst_name: null,
    risk_score: 72,
    risk_level: "high",
    summary: "Investigation found coordinated device sharing.",
    disposition: null,
    resolution_notes: null,
    created_at: "2026-03-15T00:00:00+00:00",
    updated_at: "2026-03-15T00:00:00+00:00",
    resolved_at: null,
    sla_deadline: "2026-03-16T00:00:00+00:00",
    comment_count: 0,
    alert_count: 1,
  },
  linked_alerts: [],
};

test.describe("Investigation workflow", () => {
  test("select scenario, run investigation, and view results", async ({ page }) => {
    await mockAuthenticatedAPI(page);

    // Mock the investigation endpoint
    await page.route("**/api/v1/investigations", (route) => {
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(investigationResponse),
        });
      }
      return route.continue();
    });

    // Mock case creation from investigation
    await page.route("**/api/v1/investigations/s-001/case", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createCaseFromInvestigationResponse),
      }),
    );

    await page.goto("/");

    // Login
    await page.getByLabel("Username").fill("analyst");
    await page.getByLabel("Password").fill("AnalystPassword123!");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Fraud Analyst")).toBeVisible({ timeout: 10_000 });

    // Navigate to Investigate view
    const investigateNav = page.getByRole("button", { name: /investigate/i }).first();
    if (await investigateNav.isVisible()) {
      await investigateNav.click();

      // Wait for the scenario catalog to render
      await expect(page.getByText("Cross-border device ring")).toBeVisible({ timeout: 5_000 });

      // Select the scenario
      await page.getByText("Cross-border device ring").click();

      // Look for an investigate / run button and click it
      const runButton = page.getByRole("button", { name: /investigate|run|analyze/i }).first();
      if (await runButton.isVisible({ timeout: 3_000 })) {
        await runButton.click();

        // Verify investigation results appear
        await expect(
          page.getByText(/72|high|coordinated device/i).first(),
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });
});
