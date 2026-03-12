import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/components/dashboard";
import {
  fetchAlerts,
  fetchAuditEvents,
  fetchCases,
  fetchCurrentOperator,
  fetchDashboardStats,
  fetchInvestigationClient,
  fetchScenarioCatalog,
  loginOperator,
} from "@/lib/api";
import type {
  AuditEvent,
  HealthResponse,
  InvestigationResponse,
  LoginResponse,
  OperatorPrincipal,
  ScenarioOverview,
} from "@/lib/contracts";

vi.mock("@/lib/api", () => ({
  createCase: vi.fn(),
  fetchAlerts: vi.fn(),
  fetchAuditEvents: vi.fn(),
  fetchCases: vi.fn(),
  fetchCurrentOperator: vi.fn(),
  fetchDashboardStats: vi.fn(),
  fetchInvestigationClient: vi.fn(),
  fetchScenarioCatalog: vi.fn(),
  loginOperator: vi.fn(),
  updateAlertStatus: vi.fn(),
  updateCaseStatus: vi.fn(),
}));

const mockedFetchAlerts = vi.mocked(fetchAlerts);
const mockedFetchAuditEvents = vi.mocked(fetchAuditEvents);
const mockedFetchCases = vi.mocked(fetchCases);
const mockedFetchCurrentOperator = vi.mocked(fetchCurrentOperator);
const mockedFetchDashboardStats = vi.mocked(fetchDashboardStats);
const mockedFetchInvestigationClient = vi.mocked(fetchInvestigationClient);
const mockedFetchScenarioCatalog = vi.mocked(fetchScenarioCatalog);
const mockedLoginOperator = vi.mocked(loginOperator);

const backendHealth: HealthResponse = {
  status: "ok",
  app_name: "Relational Fraud Intelligence",
  environment: "test",
  database_status: "ready",
  rate_limit_status: "ready",
  rate_limit_backend: "memory",
  seeded_scenarios: 3,
  seeded_operators: 2,
};

const scenarios: ScenarioOverview[] = [
  {
    scenario_id: "synthetic-identity-ring",
    title: "Synthetic Identity Gift Card Ring",
    industry: "Fintech",
    summary: "Gift card liquidation on shared devices.",
    hypothesis: "Synthetic identities are cashing out through digital goods.",
    tags: ["fraud", "synthetic-identity", "device-ring"],
    transaction_count: 5,
    total_volume: 4789.99,
    baseline_risk: "critical",
  },
  {
    scenario_id: "travel-ato-escalation",
    title: "Travel Account Takeover Escalation",
    industry: "Digital Banking",
    summary: "Cross-border travel spend from a new device.",
    hypothesis: "A compromised account is being rapidly monetized.",
    tags: ["fraud", "account-takeover", "cross-border"],
    transaction_count: 3,
    total_volume: 6980,
    baseline_risk: "high",
  },
];

const analystPrincipal: OperatorPrincipal = {
  user_id: "operator-analyst",
  username: "analyst",
  display_name: "Fraud Analyst",
  role: "analyst",
  is_active: true,
};

const adminPrincipal: OperatorPrincipal = {
  user_id: "operator-admin",
  username: "admin",
  display_name: "Platform Admin",
  role: "admin",
  is_active: true,
};

const auditEvents: AuditEvent[] = [
  {
    event_id: 101,
    occurred_at: "2026-03-12T14:12:00",
    request_id: "req-101",
    actor_user_id: "operator-analyst",
    actor_username: "analyst",
    actor_role: "analyst",
    action: "investigate-scenario",
    resource_type: "fraud-scenario",
    resource_id: "synthetic-identity-ring",
    http_method: "POST",
    path: "/api/v1/investigations",
    status_code: 200,
    ip_address: "127.0.0.1",
    user_agent: "vitest",
    details: {},
  },
];

function buildInvestigationResponse(
  scenario: ScenarioOverview,
): InvestigationResponse {
  return {
    investigation: {
      scenario,
      risk_level: scenario.baseline_risk,
      total_risk_score: scenario.baseline_risk === "critical" ? 92 : 76,
      summary: `${scenario.title} requires immediate review.`,
      metrics: {
        total_transaction_volume: scenario.total_volume,
        suspicious_transaction_volume: scenario.total_volume - 250,
        suspicious_transaction_count: scenario.transaction_count - 1,
        shared_device_count: 1,
        linked_customer_count: 2,
      },
      provider_summary: {
        requested_reasoning_provider: "local-rule-engine",
        active_reasoning_provider: "local-rule-engine",
        requested_text_provider: "keyword",
        active_text_provider: "keyword",
        notes: ["Deterministic fraud heuristics are active."],
      },
      top_rule_hits: [
        {
          rule_code: "shared-device-cluster",
          title: "Shared device cluster",
          weight: 28,
          narrative: "Multiple identities authenticated from the same device.",
        },
      ],
      graph_links: [
        {
          relation: "shares-device",
          explanation: "Both identities used the same low-trust device.",
          source: {
            entity_type: "customer",
            entity_id: "cust-1",
            display_name: "Amina Rahman",
          },
          target: {
            entity_type: "customer",
            entity_id: "cust-2",
            display_name: "Noah Carter",
          },
        },
      ],
      text_signals: [
        {
          signal_id: "note::1::synthetic-identity",
          provider: "keyword",
          source_kind: "investigator-note",
          source_id: "note-1",
          label: "synthetic identity",
          confidence: 0.94,
          rationale: "The note references synthetic identity behavior.",
        },
      ],
      suspicious_transactions: [
        {
          transaction_id: "txn-1",
          customer_id: "cust-1",
          account_id: "acct-1",
          device_id: "dev-1",
          merchant_id: "merchant-1",
          occurred_at: "2026-03-11T09:17:00",
          amount: 980,
          currency: "USD",
          channel: "wallet",
          status: "review",
        },
      ],
      recommended_actions: [
        "Freeze outbound spend pending enhanced verification.",
      ],
      graph_analysis: {
        connected_components: 1,
        density: 0.45,
        highest_degree_entity: { entity_type: "customer", entity_id: "cust-1", display_name: "Amina Rahman" },
        highest_degree_score: 4,
        community_count: 1,
        shortest_path_length: null,
        hub_entities: [{ entity_type: "customer", entity_id: "cust-1", display_name: "Amina Rahman" }],
        risk_amplification_factor: 1.33,
      },
    },
  };
}

function buildLoginResponse(principal: OperatorPrincipal): LoginResponse {
  return {
    access_token: `${principal.username}-token`,
    token_type: "bearer",
    expires_in_seconds: 3600,
    principal,
  };
}

describe("Dashboard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockedFetchAlerts.mockReset();
    mockedFetchAuditEvents.mockReset();
    mockedFetchCases.mockReset();
    mockedFetchCurrentOperator.mockReset();
    mockedFetchDashboardStats.mockReset();
    mockedFetchInvestigationClient.mockReset();
    mockedFetchScenarioCatalog.mockReset();
    mockedLoginOperator.mockReset();

    // Default implementations for new APIs
    mockedFetchDashboardStats.mockResolvedValue({
      stats: {
        total_scenarios: 3,
        total_cases: 0,
        open_cases: 0,
        critical_cases: 0,
        total_alerts: 0,
        unacknowledged_alerts: 0,
        avg_risk_score: 0,
        cases_by_status: {},
        alerts_by_severity: {},
        recent_activity: [],
        risk_distribution: {},
      },
    });
    mockedFetchCases.mockResolvedValue({ cases: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchAlerts.mockResolvedValue({ alerts: [], total_count: 0, page: 1, page_size: 20 });
  });

  it("renders runtime posture and requires operator sign-in", () => {
    render(<Dashboard backendHealth={backendHealth} bootstrapError={null} />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Relational Fraud Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("ready").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByText("Case management")).toBeInTheDocument();
  });

  it("authenticates an analyst, filters scenarios, and loads a different investigation", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchInvestigationClient
      .mockResolvedValueOnce(buildInvestigationResponse(scenarios[0]))
      .mockResolvedValueOnce(buildInvestigationResponse(scenarios[1]));

    render(<Dashboard backendHealth={backendHealth} bootstrapError={null} />);

    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedLoginOperator).toHaveBeenCalledWith("analyst", "AnalystPassword123!");
      expect(mockedFetchScenarioCatalog).toHaveBeenCalledWith("analyst-token");
      expect(mockedFetchInvestigationClient).toHaveBeenCalledWith(
        "analyst-token",
        "synthetic-identity-ring",
      );
    });

    // Navigate to Investigate tab
    fireEvent.click(screen.getByRole("button", { name: /Investigate/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Synthetic Identity Gift Card Ring requires immediate review."),
      ).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Search scenarios"), {
      target: { value: "travel" },
    });

    const scenarioList = within(screen.getByTestId("scenario-list"));
    expect(
      scenarioList.queryByText("Synthetic Identity Gift Card Ring"),
    ).not.toBeInTheDocument();
    expect(
      scenarioList.getByText("Travel Account Takeover Escalation"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /travel account takeover/i }));

    await waitFor(() => {
      expect(mockedFetchInvestigationClient).toHaveBeenCalledWith(
        "analyst-token",
        "travel-ato-escalation",
      );
      expect(
        screen.getByText("Travel Account Takeover Escalation requires immediate review."),
      ).toBeInTheDocument();
    });

    expect(window.localStorage.getItem("rfi.operator-token")).toBe("analyst-token");
  });

  it("loads the audit trail for an admin session", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(adminPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchInvestigationClient.mockResolvedValue(
      buildInvestigationResponse(scenarios[0]),
    );
    mockedFetchAuditEvents.mockResolvedValue({ events: auditEvents });

    render(<Dashboard backendHealth={backendHealth} bootstrapError={null} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AdminPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedFetchAuditEvents).toHaveBeenCalledWith("admin-token");
    });

    // Navigate to Audit Trail tab
    fireEvent.click(screen.getByRole("button", { name: /Audit Trail/i }));

    await waitFor(() => {
      expect(screen.getByText("investigate-scenario")).toBeInTheDocument();
    });
  });
});
