/**
 * Shared mock fixtures for Playwright E2E tests.
 *
 * Each helper registers `page.route(...)` intercepts that return realistic
 * JSON payloads matching the backend contract types, so tests never need a
 * running server.
 */

import type { Page } from "@playwright/test";

/* ------------------------------------------------------------------ */
/* Health & workspace guide (public)                                    */
/* ------------------------------------------------------------------ */

export const healthResponse = {
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

export const workspaceGuideResponse = {
  guide: {
    primary_workflow_title: "Upload → Analyze → Alert → Case",
    primary_workflow_summary: "Upload transaction data and run analysis.",
    role_stories: [],
    scoring_guarantees: [],
    llm_positioning_note: "AI explains scored results.",
  },
};

/* ------------------------------------------------------------------ */
/* Auth                                                                 */
/* ------------------------------------------------------------------ */

export const operatorPrincipal = {
  user_id: "op-001",
  username: "analyst",
  display_name: "Fraud Analyst",
  role: "analyst",
  is_active: true,
};

export const loginResponse = {
  access_token: "e2e-test-token",
  token_type: "bearer",
  expires_in_seconds: 3600,
  principal: operatorPrincipal,
};

/* ------------------------------------------------------------------ */
/* Dashboard stats                                                      */
/* ------------------------------------------------------------------ */

export const dashboardStatsResponse = {
  stats: {
    total_scenarios: 3,
    total_cases: 1,
    open_cases: 1,
    critical_cases: 0,
    total_alerts: 2,
    unacknowledged_alerts: 1,
    avg_risk_score: 55,
    cases_by_status: { open: 1 },
    alerts_by_severity: { high: 1, medium: 1 },
    recent_activity: [
      {
        event_type: "case-opened",
        description: "Test case is open.",
        actor: null,
        occurred_at: "2026-03-15T00:00:00+00:00",
        resource_id: "case-001",
      },
    ],
    risk_distribution: { high: 1 },
    total_datasets: 1,
    total_transactions_analyzed: 100,
    total_anomalies_found: 3,
    completed_analyses: 1,
    high_risk_analyses: 1,
    workflow_stages: [
      { stage_id: "upload", title: "Upload", description: "Datasets.", total_count: 1, highlighted_count: 0, highlighted_label: "waiting" },
      { stage_id: "analyze", title: "Analyze", description: "Analyses.", total_count: 1, highlighted_count: 1, highlighted_label: "high-risk" },
      { stage_id: "alert", title: "Alert", description: "Alerts.", total_count: 2, highlighted_count: 1, highlighted_label: "new" },
      { stage_id: "case", title: "Case", description: "Cases.", total_count: 1, highlighted_count: 1, highlighted_label: "open" },
    ],
    next_recommended_action: "Review the 1 unacknowledged alert(s).",
  },
};

/* ------------------------------------------------------------------ */
/* Scenarios                                                            */
/* ------------------------------------------------------------------ */

export const scenariosResponse = {
  scenarios: [
    {
      scenario_id: "s-001",
      title: "Cross-border device ring",
      industry: "Banking",
      summary: "Coordinated device sharing across borders.",
      hypothesis: "Possible synthetic identity fraud.",
      tags: ["device-ring", "cross-border"],
      transaction_count: 12,
      total_volume: 45000,
      baseline_risk: "high",
    },
  ],
};

/* ------------------------------------------------------------------ */
/* Cases                                                                */
/* ------------------------------------------------------------------ */

export const casesResponse = {
  cases: [
    {
      case_id: "case-001",
      source_type: "scenario",
      source_id: "s-001",
      scenario_id: "s-001",
      title: "Cross-border device ring",
      status: "open",
      priority: "high",
      assigned_analyst_id: null,
      assigned_analyst_name: null,
      risk_score: 72,
      risk_level: "high",
      summary: "Case summary.",
      disposition: null,
      resolution_notes: null,
      created_at: "2026-03-15T00:00:00+00:00",
      updated_at: "2026-03-15T00:00:00+00:00",
      resolved_at: null,
      sla_deadline: "2026-03-16T00:00:00+00:00",
      comment_count: 0,
      alert_count: 2,
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 20,
};

/* ------------------------------------------------------------------ */
/* Alerts                                                               */
/* ------------------------------------------------------------------ */

export const alertsResponse = {
  alerts: [
    {
      alert_id: "alert-001",
      source_type: "scenario",
      source_id: "s-001",
      scenario_id: "s-001",
      rule_code: "device-ring",
      title: "Device coordination alert",
      severity: "high",
      status: "new",
      narrative: "Shared device cluster detected.",
      assigned_analyst_id: null,
      assigned_analyst_name: null,
      linked_case_id: null,
      created_at: "2026-03-15T00:00:00+00:00",
      acknowledged_at: null,
      resolved_at: null,
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 20,
};

/* ------------------------------------------------------------------ */
/* Audit events                                                         */
/* ------------------------------------------------------------------ */

export const auditEventsResponse = { events: [] };

/* ------------------------------------------------------------------ */
/* Datasets                                                             */
/* ------------------------------------------------------------------ */

export const datasetsResponse = { datasets: [] };

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
/* ------------------------------------------------------------------ */

export async function mockPublicAPI(page: Page): Promise<void> {
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(healthResponse) }),
  );
  await page.route("**/api/v1/workspace/guide", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(workspaceGuideResponse) }),
  );
}

export async function mockAuthenticatedAPI(page: Page): Promise<void> {
  await mockPublicAPI(page);

  await page.route("**/api/v1/auth/token", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(loginResponse) }),
  );
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ principal: operatorPrincipal }) }),
  );
  await page.route("**/api/v1/dashboard/stats", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(dashboardStatsResponse) }),
  );
  await page.route("**/api/v1/scenarios", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(scenariosResponse) }),
  );
  await page.route("**/api/v1/cases?**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(casesResponse) }),
  );
  await page.route("**/api/v1/cases", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(casesResponse) }),
  );
  await page.route("**/api/v1/alerts?**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(alertsResponse) }),
  );
  await page.route("**/api/v1/alerts", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(alertsResponse) }),
  );
  await page.route("**/api/v1/audit-events**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auditEventsResponse) }),
  );
  await page.route("**/api/v1/datasets", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(datasetsResponse) }),
  );
}

