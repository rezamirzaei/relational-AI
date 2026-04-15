import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchCurrentOperator,
  fetchScenarioCatalog,
  fetchScenarioDetail,
  fetchAuditEvents,
  fetchDashboardStats,
  fetchCases,
  fetchAlerts,
  fetchDatasets,
  runDraftInvestigation,
  loginOperator,
} from "@/lib/api";
import type { HealthResponse, OperatorPrincipal } from "@/lib/contracts";
import { useDashboardState } from "@/lib/use-dashboard-state";

type SubmitEvent = React.FormEvent<HTMLFormElement>;

function createSubmitEvent(): SubmitEvent {
  return Object.assign(new Event("submit"), { preventDefault: vi.fn() }) as unknown as SubmitEvent;
}

vi.mock("@/lib/api", () => ({
  addCaseComment: vi.fn(),
  analyzeDataset: vi.fn(),
  createCase: vi.fn(),
  createCaseFromAnalysis: vi.fn(),
  createCaseFromAlert: vi.fn(),
  createCaseFromInvestigation: vi.fn(),
  fetchAlerts: vi.fn(),
  fetchAnalysisExplanation: vi.fn(),
  fetchAnalysisResult: vi.fn(),
  fetchAuditEvents: vi.fn(),
  fetchCase: vi.fn(),
  fetchCases: vi.fn(),
  fetchCurrentOperator: vi.fn(),
  fetchDashboardStats: vi.fn(),
  fetchDatasets: vi.fn(),
  fetchInvestigationClient: vi.fn(),
  fetchScenarioCatalog: vi.fn(),
  fetchScenarioDetail: vi.fn(),
  loginOperator: vi.fn(),
  runDraftInvestigation: vi.fn(),
  updateAlertStatus: vi.fn(),
  updateCaseStatus: vi.fn(),
  uploadDataset: vi.fn(),
}));

const mockedLoginOperator = vi.mocked(loginOperator);
const mockedFetchCurrentOperator = vi.mocked(fetchCurrentOperator);
const mockedFetchScenarioCatalog = vi.mocked(fetchScenarioCatalog);
const mockedFetchScenarioDetail = vi.mocked(fetchScenarioDetail);
const mockedFetchAuditEvents = vi.mocked(fetchAuditEvents);
const mockedFetchDashboardStats = vi.mocked(fetchDashboardStats);
const mockedFetchCases = vi.mocked(fetchCases);
const mockedFetchAlerts = vi.mocked(fetchAlerts);
const mockedFetchDatasets = vi.mocked(fetchDatasets);
const mockedRunDraftInvestigation = vi.mocked(runDraftInvestigation);

const backendHealth: HealthResponse = {
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

const analystPrincipal: OperatorPrincipal = {
  user_id: "operator-analyst",
  username: "analyst",
  display_name: "Fraud Analyst",
  role: "analyst",
  is_active: true,
};

const emptyStats = {
  stats: {
    total_scenarios: 0,
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
    completed_analyses: 0,
    high_risk_analyses: 0,
    workflow_stages: [],
    next_recommended_action: "Upload a dataset to start.",
  },
};

describe("useDashboardState", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.resetAllMocks();
    mockedFetchDashboardStats.mockResolvedValue(emptyStats);
    mockedFetchCases.mockResolvedValue({ cases: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchAlerts.mockResolvedValue({ alerts: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchDatasets.mockResolvedValue({ datasets: [] });
    mockedFetchScenarioDetail.mockResolvedValue({
      scenario: {
        scenario_id: "draft-scenario",
        title: "Draft scenario",
        industry: "finance",
        summary: "summary",
        hypothesis: "hypothesis",
        tags: ["fraud"],
        customers: [],
        accounts: [],
        devices: [],
        merchants: [],
        transactions: [],
        investigator_notes: [],
      },
    });
    mockedRunDraftInvestigation.mockResolvedValue({
      investigation: {
        scenario: {
          scenario_id: "draft-scenario",
          title: "Draft scenario",
          industry: "finance",
          summary: "summary",
          hypothesis: "hypothesis",
          tags: ["fraud"],
          transaction_count: 0,
          total_volume: 0,
          baseline_risk: "medium",
        },
        risk_level: "medium",
        total_risk_score: 40,
        summary: "Draft scenario reviewed.",
        metrics: {
          total_transaction_volume: 0,
          suspicious_transaction_volume: 0,
          suspicious_transaction_count: 0,
          shared_device_count: 0,
          linked_customer_count: 0,
        },
        provider_summary: {
          requested_reasoning_provider: "local-rule-engine",
          active_reasoning_provider: "local-rule-engine",
          requested_text_provider: "keyword",
          active_text_provider: "keyword",
          notes: [],
          semantic_model: null,
        },
        top_rule_hits: [],
        graph_links: [],
        text_signals: [],
        suspicious_transactions: [],
        recommended_actions: [],
        investigation_leads: [],
        graph_analysis: null,
      },
    });
  });

  it("returns correct initial state shape", () => {
    const { result } = renderHook(() => useDashboardState(backendHealth, null));
    const [state] = result.current;

    expect(state.authToken).toBeNull();
    expect(state.operator).toBeNull();
    expect(state.activeView).toBe("overview");
    expect(state.username).toBe("");
    expect(state.password).toBe("");
    expect(state.isAuthenticating).toBe(false);
    expect(state.loginError).toBeNull();
    expect(state.errorMessage).toBeNull();
    expect(state.scenarios).toEqual([]);
    expect(state.cases).toEqual([]);
    expect(state.alerts).toEqual([]);
    expect(state.datasets).toEqual([]);
    expect(state.showBootstrapCredentials).toBe(true);
  });

  it("propagates bootstrapError as errorMessage", () => {
    const { result } = renderHook(() =>
      useDashboardState(null, "Backend unreachable"),
    );
    const [state] = result.current;
    expect(state.errorMessage).toBe("Backend unreachable");
  });

  it("shows bootstrap credentials for test/local environments", () => {
    const { result: testResult } = renderHook(() =>
      useDashboardState(backendHealth, null),
    );
    expect(testResult.current[0].showBootstrapCredentials).toBe(true);

    const prodHealth = { ...backendHealth, environment: "production" };
    const { result: prodResult } = renderHook(() =>
      useDashboardState(prodHealth, null),
    );
    expect(prodResult.current[0].showBootstrapCredentials).toBe(false);
  });

  it("handles login flow — sets token, operator, and navigates to default view", async () => {
    mockedLoginOperator.mockResolvedValue({
      access_token: "test-token",
      token_type: "bearer",
      expires_in_seconds: 3600,
      principal: analystPrincipal,
    });
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios: [] });

    const { result } = renderHook(() => useDashboardState(backendHealth, null));

    act(() => {
      result.current[1].setUsername("analyst");
      result.current[1].setPassword("AnalystPassword123!");
    });

    expect(result.current[0].username).toBe("analyst");
    expect(result.current[0].password).toBe("AnalystPassword123!");

    const fakeEvent = createSubmitEvent();
    await act(async () => {
      await result.current[1].handleLogin(fakeEvent);
    });

    expect(fakeEvent.preventDefault).toHaveBeenCalled();
    expect(mockedLoginOperator).toHaveBeenCalledWith("analyst", "AnalystPassword123!");
    expect(result.current[0].authToken).toBe("test-token");
    expect(result.current[0].operator).toEqual(analystPrincipal);
    // Analyst default view is "analyze"
    expect(result.current[0].activeView).toBe("analyze");
    // Password cleared after login
    expect(result.current[0].password).toBe("");
  });

  it("handles logout — clears all state", async () => {
    mockedLoginOperator.mockResolvedValue({
      access_token: "test-token",
      token_type: "bearer",
      expires_in_seconds: 3600,
      principal: analystPrincipal,
    });
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios: [] });

    const { result } = renderHook(() => useDashboardState(backendHealth, null));

    const fakeEvent = createSubmitEvent();
    await act(async () => {
      result.current[1].setUsername("analyst");
      result.current[1].setPassword("test");
      await result.current[1].handleLogin(fakeEvent);
    });

    expect(result.current[0].authToken).toBe("test-token");

    act(() => {
      result.current[1].handleLogout();
    });

    expect(result.current[0].authToken).toBeNull();
    expect(result.current[0].operator).toBeNull();
    expect(result.current[0].activeView).toBe("overview");
    expect(result.current[0].scenarios).toEqual([]);
    expect(window.localStorage.getItem("rfi.operator-token")).toBeNull();
  });

  it("handles login error gracefully", async () => {
    mockedLoginOperator.mockRejectedValue(new Error("Invalid credentials"));

    const { result } = renderHook(() => useDashboardState(backendHealth, null));

    act(() => {
      result.current[1].setUsername("bad");
      result.current[1].setPassword("bad");
    });

    const fakeEvent = createSubmitEvent();
    await act(async () => {
      await result.current[1].handleLogin(fakeEvent);
    });

    expect(result.current[0].loginError).toBe("Invalid credentials");
    expect(result.current[0].authToken).toBeNull();
    expect(result.current[0].isAuthenticating).toBe(false);
  });

  it("changes view via setActiveView", () => {
    const { result } = renderHook(() => useDashboardState(backendHealth, null));

    act(() => {
      result.current[1].setActiveView("alerts");
    });

    expect(result.current[0].activeView).toBe("alerts");
  });

  it("filters scenarios by search query", async () => {
    mockedLoginOperator.mockResolvedValue({
      access_token: "test-token",
      token_type: "bearer",
      expires_in_seconds: 3600,
      principal: analystPrincipal,
    });
    mockedFetchScenarioCatalog.mockResolvedValue({
      scenarios: [
        {
          scenario_id: "s1",
          title: "Gift Card Fraud",
          industry: "Fintech",
          summary: "Gift card abuse",
          hypothesis: "Test",
          tags: ["fraud"],
          transaction_count: 5,
          total_volume: 1000,
          baseline_risk: "high",
        },
        {
          scenario_id: "s2",
          title: "Travel ATO",
          industry: "Banking",
          summary: "Cross-border takeover",
          hypothesis: "Test",
          tags: ["account-takeover"],
          transaction_count: 3,
          total_volume: 5000,
          baseline_risk: "medium",
        },
      ],
    });

    const { result } = renderHook(() => useDashboardState(backendHealth, null));

    const fakeEvent = createSubmitEvent();
    await act(async () => {
      result.current[1].setUsername("analyst");
      result.current[1].setPassword("test");
      await result.current[1].handleLogin(fakeEvent);
    });

    expect(result.current[0].visibleScenarios).toHaveLength(2);

    act(() => {
      result.current[1].setSearchQuery("travel");
    });

    // useDeferredValue may need a tick to settle
    await waitFor(() => {
      expect(result.current[0].visibleScenarios).toHaveLength(1);
      expect(result.current[0].visibleScenarios[0].title).toBe("Travel ATO");
    });
  });
});
