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
  analyzeDataset,
  fetchAlerts,
  fetchAuditEvents,
  fetchCases,
  fetchCurrentOperator,
  fetchDashboardStats,
  fetchDatasets,
  fetchInvestigationClient,
  fetchScenarioCatalog,
  loginOperator,
} from "@/lib/api";
import type {
  AnalysisResponse,
  DatasetListResponse,
  AuditEvent,
  ListAlertsResponse,
  HealthResponse,
  InvestigationResponse,
  LoginResponse,
  OperatorPrincipal,
  ScenarioOverview,
} from "@/lib/contracts";

vi.mock("@/lib/api", () => ({
  analyzeDataset: vi.fn(),
  createCase: vi.fn(),
  fetchAlerts: vi.fn(),
  fetchAuditEvents: vi.fn(),
  fetchCases: vi.fn(),
  fetchCurrentOperator: vi.fn(),
  fetchDashboardStats: vi.fn(),
  fetchDatasets: vi.fn(),
  fetchInvestigationClient: vi.fn(),
  fetchScenarioCatalog: vi.fn(),
  loginOperator: vi.fn(),
  updateAlertStatus: vi.fn(),
  updateCaseStatus: vi.fn(),
}));

const mockedAnalyzeDataset = vi.mocked(analyzeDataset);
const mockedFetchAlerts = vi.mocked(fetchAlerts);
const mockedFetchAuditEvents = vi.mocked(fetchAuditEvents);
const mockedFetchCases = vi.mocked(fetchCases);
const mockedFetchCurrentOperator = vi.mocked(fetchCurrentOperator);
const mockedFetchDatasets = vi.mocked(fetchDatasets);
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

const uploadedDatasetList: DatasetListResponse = {
  datasets: [
    {
      dataset_id: "dataset-1",
      name: "march-transactions.csv",
      uploaded_at: "2026-03-12T14:00:00",
      row_count: 128,
      status: "uploaded",
      error_message: null,
    },
  ],
};

const completedDatasetList: DatasetListResponse = {
  datasets: [
    {
      dataset_id: "dataset-1",
      name: "march-transactions.csv",
      uploaded_at: "2026-03-12T14:00:00",
      row_count: 128,
      status: "completed",
      error_message: null,
    },
  ],
};

const initialAlertList: ListAlertsResponse = {
  alerts: [],
  total_count: 0,
  page: 1,
  page_size: 20,
};

const generatedAlertList: ListAlertsResponse = {
  alerts: [
    {
      alert_id: "alert-1",
      source_type: "dataset",
      source_id: "dataset-1",
      scenario_id: null,
      rule_code: "velocity-spike",
      title: "Velocity spike in dataset-1",
      severity: "high",
      status: "new",
      narrative: "Analysis detected a concentrated burst of high-value activity.",
      assigned_analyst_id: null,
      assigned_analyst_name: null,
      linked_case_id: null,
      created_at: "2026-03-12T14:05:00",
      acknowledged_at: null,
      resolved_at: null,
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 20,
};

const datasetAnalysisResponse: AnalysisResponse = {
  analysis: {
    analysis_id: "analysis-1",
    dataset_id: "dataset-1",
    completed_at: "2026-03-12T14:05:00",
    total_transactions: 128,
    total_anomalies: 3,
    risk_score: 68,
    risk_level: "high",
    benford_chi_squared: 18.4,
    benford_p_value: 0.0021,
    benford_is_suspicious: true,
    benford_digits: [
      { digit: 1, expected_pct: 30.1, actual_pct: 18.4, deviation: -11.7 },
      { digit: 2, expected_pct: 17.6, actual_pct: 22.1, deviation: 4.5 },
    ],
    outlier_count: 2,
    outlier_pct: 1.6,
    velocity_spikes: [
      {
        entity_id: "acct-77",
        entity_type: "account",
        window_start: "2026-03-12T13:00:00",
        window_end: "2026-03-12T14:00:00",
        transaction_count: 7,
        total_amount: 12400,
        baseline_avg_count: 1.1,
        z_score: 4.8,
      },
    ],
    graph_analysis: null,
    anomalies: [
      {
        anomaly_id: "anom-1",
        anomaly_type: "velocity",
        severity: "high",
        title: "Velocity spike",
        description: "Rapid sequence of high-value transactions.",
        affected_entity_id: "acct-77",
        affected_entity_type: "account",
        score: 0.91,
        evidence: {},
      },
    ],
    summary: "Dataset analysis generated a high-risk alert candidate.",
  },
};

const refreshedAuditEvents: AuditEvent[] = [
  {
    event_id: 102,
    occurred_at: "2026-03-12T14:05:00",
    request_id: "req-102",
    actor_user_id: "operator-admin",
    actor_username: "admin",
    actor_role: "admin",
    action: "analyze-dataset",
    resource_type: "dataset",
    resource_id: "dataset-1",
    http_method: "POST",
    path: "/api/v1/datasets/dataset-1/analyze",
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
    mockedAnalyzeDataset.mockReset();
    mockedFetchAlerts.mockReset();
    mockedFetchAuditEvents.mockReset();
    mockedFetchCases.mockReset();
    mockedFetchCurrentOperator.mockReset();
    mockedFetchDatasets.mockReset();
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
        total_datasets: 0,
        total_transactions_analyzed: 0,
        total_anomalies_found: 0,
      },
    });
    mockedFetchCases.mockResolvedValue({ cases: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchAlerts.mockResolvedValue({ alerts: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchDatasets.mockResolvedValue({ datasets: [] });
  });

  it("renders runtime posture and requires operator sign-in", () => {
    render(<Dashboard backendHealth={backendHealth} bootstrapError={null} />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Relational Fraud Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("ready").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByText("Persistent alerts")).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByText("Local bootstrap operators")).toBeInTheDocument();
  });

  it("authenticates an analyst, filters scenarios, and loads a different investigation", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchInvestigationClient
      .mockResolvedValueOnce(buildInvestigationResponse(scenarios[0]))
      .mockResolvedValueOnce(buildInvestigationResponse(scenarios[1]));

    render(<Dashboard backendHealth={backendHealth} bootstrapError={null} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedLoginOperator).toHaveBeenCalledWith("analyst", "AnalystPassword123!");
      expect(mockedFetchScenarioCatalog).toHaveBeenCalledWith("analyst-token");
    });

    fireEvent.click(screen.getByRole("button", { name: /Reference Scenarios/i }));
    fireEvent.click(screen.getByRole("button", { name: /synthetic identity gift card ring/i }));

    await waitFor(() => {
      expect(mockedFetchInvestigationClient).toHaveBeenCalledWith(
        "analyst-token",
        "synthetic-identity-ring",
      );
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

  it("refreshes alerts and audit entries after an admin analyzes a dataset", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(adminPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchAuditEvents
      .mockResolvedValueOnce({ events: auditEvents })
      .mockResolvedValueOnce({ events: refreshedAuditEvents });
    mockedFetchDatasets
      .mockResolvedValueOnce(uploadedDatasetList)
      .mockResolvedValueOnce(completedDatasetList);
    mockedFetchAlerts
      .mockResolvedValueOnce(initialAlertList)
      .mockResolvedValueOnce(generatedAlertList);
    mockedFetchDashboardStats
      .mockResolvedValueOnce({
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
          total_datasets: 1,
          total_transactions_analyzed: 0,
          total_anomalies_found: 0,
        },
      })
      .mockResolvedValueOnce({
        stats: {
          total_scenarios: 3,
          total_cases: 0,
          open_cases: 0,
          critical_cases: 0,
          total_alerts: 1,
          unacknowledged_alerts: 1,
          avg_risk_score: 68,
          cases_by_status: {},
          alerts_by_severity: { high: 1 },
          recent_activity: [],
          risk_distribution: { high: 1 },
          total_datasets: 1,
          total_transactions_analyzed: 128,
          total_anomalies_found: 3,
        },
      });
    mockedAnalyzeDataset.mockResolvedValue(datasetAnalysisResponse);

    render(<Dashboard backendHealth={backendHealth} bootstrapError={null} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AdminPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedFetchDatasets).toHaveBeenCalledWith("admin-token");
    });

    fireEvent.click(screen.getByRole("button", { name: /Analyze Data/i }));
    fireEvent.click(screen.getByRole("button", { name: /Run Fraud Analysis/i }));

    await waitFor(() => {
      expect(mockedAnalyzeDataset).toHaveBeenCalledWith("admin-token", "dataset-1");
      expect(screen.getByText("Dataset analysis generated a high-risk alert candidate.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Alerts/i }));

    await waitFor(() => {
      expect(screen.getByText("Velocity spike in dataset-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Audit Trail/i }));

    await waitFor(() => {
      expect(mockedFetchAuditEvents).toHaveBeenCalledTimes(2);
      expect(screen.getByText("analyze-dataset")).toBeInTheDocument();
    });
  });
});
