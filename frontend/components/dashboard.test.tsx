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
  addCaseComment,
  analyzeDataset,
  createCaseFromAnalysis,
  createCaseFromAlert,
  createCaseFromInvestigation,
  fetchAlerts,
  fetchAnalysisExplanation,
  fetchAnalysisResult,
  fetchAuditEvents,
  fetchCase,
  fetchCases,
  fetchCurrentOperator,
  fetchDashboardStats,
  fetchDatasets,
  fetchInvestigationClient,
  fetchScenarioCatalog,
  loginOperator,
  updateCaseStatus,
} from "@/lib/api";
import type {
  AnalysisResponse,
  AnalysisExplanationResponse,
  CreateCaseFromAlertResponse,
  CreateCaseFromAnalysisResponse,
  CreateCaseFromInvestigationResponse,
  DatasetListResponse,
  AuditEvent,
  GetCaseResponse,
  ListAlertsResponse,
  ListCasesResponse,
  HealthResponse,
  InvestigationResponse,
  LoginResponse,
  OperatorPrincipal,
  ScenarioOverview,
  WorkspaceGuide,
} from "@/lib/contracts";

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
  loginOperator: vi.fn(),
  updateAlertStatus: vi.fn(),
  updateCaseStatus: vi.fn(),
  uploadDataset: vi.fn(),
}));

const mockedAddCaseComment = vi.mocked(addCaseComment);
const mockedAnalyzeDataset = vi.mocked(analyzeDataset);
const mockedCreateCaseFromAnalysis = vi.mocked(createCaseFromAnalysis);
const mockedCreateCaseFromAlert = vi.mocked(createCaseFromAlert);
const mockedCreateCaseFromInvestigation = vi.mocked(createCaseFromInvestigation);
const mockedFetchAlerts = vi.mocked(fetchAlerts);
const mockedFetchAnalysisExplanation = vi.mocked(fetchAnalysisExplanation);
const mockedFetchAnalysisResult = vi.mocked(fetchAnalysisResult);
const mockedFetchAuditEvents = vi.mocked(fetchAuditEvents);
const mockedFetchCase = vi.mocked(fetchCase);
const mockedFetchCases = vi.mocked(fetchCases);
const mockedFetchCurrentOperator = vi.mocked(fetchCurrentOperator);
const mockedFetchDatasets = vi.mocked(fetchDatasets);
const mockedFetchDashboardStats = vi.mocked(fetchDashboardStats);
const mockedFetchInvestigationClient = vi.mocked(fetchInvestigationClient);
const mockedFetchScenarioCatalog = vi.mocked(fetchScenarioCatalog);
const mockedLoginOperator = vi.mocked(loginOperator);
const mockedUpdateCaseStatus = vi.mocked(updateCaseStatus);

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

const workspaceGuide: WorkspaceGuide = {
  primary_workflow_title: "Primary Workflow: Upload -> Analyze -> Alert -> Case",
  primary_workflow_summary:
    "The main product path starts with transaction data. Analysts upload a dataset, run statistical and behavioral analysis, review alerts, and open a case when the evidence warrants it.",
  role_stories: [
    {
      story_id: "frontline-analyst",
      persona_name: "Nadia",
      title: "Frontline Fraud Analyst",
      platform_role: "analyst",
      goal: "Turn suspicious uploaded data into a triaged case quickly.",
      workflow_steps: [
        "Upload a transaction export.",
        "Run statistical and behavioral analysis.",
        "Open a case from the strongest findings.",
      ],
      success_signal: "A high-risk dataset becomes an alert-backed case in one pass.",
      recommended_view: "analyze",
    },
    {
      story_id: "queue-owner",
      persona_name: "Marcus",
      title: "Queue Owner Analyst",
      platform_role: "analyst",
      goal: "Keep the alert queue moving.",
      workflow_steps: [
        "Review new alerts.",
        "Prioritize open cases.",
        "Resolve false positives or escalate fraud.",
      ],
      success_signal: "New alerts do not sit unacknowledged.",
      recommended_view: "alerts",
    },
    {
      story_id: "platform-admin",
      persona_name: "Priya",
      title: "Platform Administrator",
      platform_role: "admin",
      goal: "Verify the workflow is healthy and auditable.",
      workflow_steps: [
        "Check throughput and queue pressure.",
        "Inspect audit activity.",
        "Confirm the platform is stable.",
      ],
      success_signal: "The platform stays trustworthy while analysts work the queue.",
      recommended_view: "overview",
    },
  ],
  scoring_guarantees: [
    "Risk scores are computed from scored findings.",
    "Alert thresholds are fixed.",
    "Cases stay linked to persistent workflow records.",
  ],
  llm_positioning_note:
    "The copilot layer explains scored results. It does not change risk scores, suppress alerts, or open cases on its own.",
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

const linkedAlertList: ListAlertsResponse = {
  alerts: [
    {
      ...generatedAlertList.alerts[0],
      status: "investigating",
      linked_case_id: "case-from-alert-1",
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 20,
};

const linkedAlertListFromAnalysis: ListAlertsResponse = {
  alerts: [
    {
      ...generatedAlertList.alerts[0],
      title: "Potential shared-device coordination ring",
      status: "investigating",
      linked_case_id: "case-analysis-1",
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 20,
};

const caseFromAlertResponse: CreateCaseFromAlertResponse = {
  alert: linkedAlertList.alerts[0],
  case: {
    case_id: "case-from-alert-1",
    source_type: "dataset",
    source_id: "dataset-1",
    scenario_id: null,
    title: "Alert review: Velocity spike in dataset-1",
    status: "open",
    priority: "high",
    assigned_analyst_id: null,
    assigned_analyst_name: null,
    risk_score: 68,
    risk_level: "high",
    summary: "Dataset analysis generated a high-risk alert candidate.",
    disposition: null,
    resolution_notes: null,
    created_at: "2026-03-12T14:07:00",
    updated_at: "2026-03-12T14:07:00",
    resolved_at: null,
    sla_deadline: "2026-03-13T14:07:00",
    comment_count: 0,
    alert_count: 0,
  },
};

const caseFromAlertList: ListCasesResponse = {
  cases: [caseFromAlertResponse.case],
  total_count: 1,
  page: 1,
  page_size: 20,
};

const caseFromAnalysisResponse: CreateCaseFromAnalysisResponse = {
  analysis: {} as AnalysisResponse["analysis"],
  case: {
    case_id: "case-analysis-1",
    source_type: "dataset",
    source_id: "dataset-1",
    scenario_id: null,
    title: "march-transactions.csv: Potential shared-device coordination ring",
    status: "open",
    priority: "high",
    assigned_analyst_id: null,
    assigned_analyst_name: null,
    risk_score: 68,
    risk_level: "high",
    summary:
      "Primary lead: Potential shared-device coordination ring. Multiple accounts are converging on the same device.",
    disposition: null,
    resolution_notes: null,
    created_at: "2026-03-12T14:08:00",
    updated_at: "2026-03-12T14:08:00",
    resolved_at: null,
    sla_deadline: "2026-03-13T14:08:00",
    comment_count: 0,
    alert_count: 0,
  },
  linked_alerts: linkedAlertListFromAnalysis.alerts,
};

const caseFromAnalysisList: ListCasesResponse = {
  cases: [caseFromAnalysisResponse.case],
  total_count: 1,
  page: 1,
  page_size: 20,
};

const openCaseList: ListCasesResponse = {
  cases: [caseFromAlertResponse.case],
  total_count: 1,
  page: 1,
  page_size: 20,
};

const resolvedCaseList: ListCasesResponse = {
  cases: [
    {
      ...caseFromAlertResponse.case,
      status: "resolved",
      disposition: "confirmed-fraud",
      resolution_notes: "Confirmed during analyst review.",
      resolved_at: "2026-03-12T15:20:00",
      updated_at: "2026-03-12T15:20:00",
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
    graph_analysis: {
      connected_components: 2,
      density: 0.24,
      highest_degree_entity: {
        entity_type: "device",
        entity_id: "fp-ring-shared-01",
        display_name: "fp-ring-shared-01",
      },
      highest_degree_score: 4,
      community_count: 2,
      shortest_path_length: 2,
      hub_entities: [
        {
          entity_type: "device",
          entity_id: "fp-ring-shared-01",
          display_name: "fp-ring-shared-01",
        },
      ],
      risk_amplification_factor: 1.22,
    },
    behavioral_insights: [
      {
        insight_id: "shared-device::fp-ring-shared-01",
        title: "Shared device links multiple accounts",
        severity: "high",
        narrative:
          "Device fp-ring-shared-01 touched 3 accounts across 12 transactions totaling $8,420.00.",
        entities: [
          {
            entity_type: "device",
            entity_id: "fp-ring-shared-01",
            display_name: "fp-ring-shared-01",
          },
          {
            entity_type: "account",
            entity_id: "acct-77",
            display_name: "acct-77",
          },
        ],
        evidence: {
          account_count: 3,
          transaction_count: 12,
        },
      },
    ],
    investigation_leads: [
      {
        lead_id: "lead::shared-device::fp-ring-shared-01",
        lead_type: "shared-device-ring",
        title: "Potential shared-device coordination ring",
        severity: "high",
        hypothesis:
          "Multiple accounts are converging on the same device, which is consistent with coordinated cash-out or synthetic identity reuse.",
        narrative:
          "Device fp-ring-shared-01 touched 3 accounts across 12 transactions totaling $8,420.00. The relationship graph amplified this cluster to 1.22x baseline risk.",
        entities: [
          {
            entity_type: "device",
            entity_id: "fp-ring-shared-01",
            display_name: "fp-ring-shared-01",
          },
          {
            entity_type: "account",
            entity_id: "acct-77",
            display_name: "acct-77",
          },
        ],
        supporting_anomaly_ids: ["shared-device::fp-ring-shared-01"],
        recommended_actions: [
          "Confirm whether the linked accounts share a legitimate owner or onboarding trail.",
          "Review device binding, login, and credential-reset history for the linked accounts.",
        ],
        evidence: {
          supporting_amount: 8420,
        },
      },
    ],
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

const datasetAnalysisExplanation: AnalysisExplanationResponse = {
  explanation: {
    dataset_id: "dataset-1",
    dataset_name: "march-transactions.csv",
    audience: "admin",
    headline: "march-transactions.csv is a high-priority review candidate at 68/100.",
    narrative:
      "The dataset was scored from dataset-derived statistical and behavioral inference. Review the strongest anomaly evidence before opening or updating a case.",
    deterministic_evidence: [
      "Risk score: 68/100 from statistical anomaly weights, density, and relationship structure.",
      "Total anomalies: 3 across 128 transactions.",
    ],
    recommended_actions: [
      "Review the generated alerts before they fall behind the queue.",
      "Open or update a case so the evidence trail stays attached to the dataset.",
    ],
    watchouts: [
      "The explanation layer is advisory. Statistical and behavioral scoring remain the source of truth.",
    ],
    provider_summary: {
      requested_provider: "deterministic",
      active_provider: "deterministic",
      source_of_truth: "statistical-and-behavioral-analysis",
      notes: [
        "This brief is generated from the dataset's statistical and behavioral scoring outputs.",
      ],
    },
  },
};

const caseDetailFromAlertResponse: GetCaseResponse = {
  case: caseFromAlertResponse.case,
  comments: [],
  related_alerts: linkedAlertList.alerts,
  investigation: null,
  analysis: datasetAnalysisResponse.analysis,
  dataset: {
    dataset_id: "dataset-1",
    name: "march-transactions.csv",
    uploaded_at: "2026-03-12T14:00:00",
    row_count: 128,
    status: "completed",
    error_message: null,
  },
  scenario_transactions: [],
  dataset_transactions: [
    {
      row_index: 0,
      transaction_id: "txn-1001",
      account_id: "acct-77",
      amount: 12400,
      timestamp: "2026-03-12T13:12:00",
      merchant: "Global Travel Hub",
      category: "travel",
      device_fingerprint: "fp-ring-shared-01",
      ip_country: "GB",
      channel: "wallet",
      is_fraud_label: null,
    },
  ],
  investigator_notes: [],
};

const caseDetailWithCommentResponse: GetCaseResponse = {
  ...caseDetailFromAlertResponse,
  case: {
    ...caseFromAlertResponse.case,
    comment_count: 1,
  },
  comments: [
    {
      comment_id: "comment-1",
      case_id: "case-from-alert-1",
      author_id: "operator-analyst",
      author_name: "Fraud Analyst",
      body: "Reviewed the linked transactions and escalated the merchant/device overlap.",
      created_at: "2026-03-12T14:21:00",
    },
  ],
};

const resolvedCaseDetailResponse: GetCaseResponse = {
  ...caseDetailFromAlertResponse,
  case: resolvedCaseList.cases[0],
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
        semantic_model: {
          concept_names: ["Customer", "Device", "Merchant", "Transaction"],
          relationship_names: [
            "customer_uses_device",
            "customer_transacts_with_merchant",
          ],
          derived_rule_names: ["shared-low-trust-device-exposure"],
          query_blueprints: [
            {
              code: "shared-low-trust-devices",
              description: "Find customers connected through low-trust devices.",
            },
          ],
          seeded_fact_count: 18,
          compiled_type_count: 10,
          compiled_relation_count: 9,
          execution_posture:
            "Local showcase mode compiles the semantic fraud model into a RelationalAI metamodel without requiring remote query execution.",
        },
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
      investigation_leads: [
        {
          lead_id: "scenario-lead::shared-device-ring",
          lead_type: "shared-device-ring",
          title: "Potential shared-device coordination ring",
          severity: "high",
          hypothesis:
            "Multiple customers are converging on the same device, which is consistent with a coordinated identity ring or linked account takeover.",
          narrative:
            "Multiple identities authenticated from the same device. The relationship graph amplified the cluster to 1.33x baseline risk.",
          entities: [
            {
              entity_type: "customer",
              entity_id: "cust-1",
              display_name: "Amina Rahman",
            },
            {
              entity_type: "customer",
              entity_id: "cust-2",
              display_name: "Noah Carter",
            },
          ],
          supporting_anomaly_ids: ["shared-device-cluster"],
          recommended_actions: [
            "Validate whether the linked customers have a legitimate shared owner or household.",
            "Review device binding, credential-reset history, and recent login telemetry.",
          ],
          evidence: {
            supporting_amount: 28,
          },
        },
      ],
      graph_analysis: {
        connected_components: 1,
        density: 0.45,
        highest_degree_entity: {
          entity_type: "customer",
          entity_id: "cust-1",
          display_name: "Amina Rahman",
        },
        highest_degree_score: 4,
        community_count: 1,
        shortest_path_length: null,
        hub_entities: [
          {
            entity_type: "customer",
            entity_id: "cust-1",
            display_name: "Amina Rahman",
          },
        ],
        risk_amplification_factor: 1.33,
      },
    },
  };
}

function buildCreateCaseFromInvestigationResponse(
  scenario: ScenarioOverview,
): CreateCaseFromInvestigationResponse {
  return {
    investigation: buildInvestigationResponse(scenario).investigation,
    case: {
      case_id: "case-from-investigation-1",
      source_type: "scenario",
      source_id: scenario.scenario_id,
      scenario_id: scenario.scenario_id,
      title: `${scenario.title}: Potential shared-device coordination ring`,
      status: "open",
      priority: scenario.baseline_risk,
      assigned_analyst_id: null,
      assigned_analyst_name: null,
      risk_score: scenario.baseline_risk === "critical" ? 92 : 76,
      risk_level: scenario.baseline_risk,
      summary:
        "Primary lead: Potential shared-device coordination ring. Multiple customers are converging on the same device.",
      disposition: null,
      resolution_notes: null,
      created_at: "2026-03-12T10:00:00",
      updated_at: "2026-03-12T10:00:00",
      resolved_at: null,
      sla_deadline: "2026-03-13T10:00:00",
      comment_count: 0,
      alert_count: 0,
    },
    linked_alerts: [
      {
        alert_id: "scenario-alert-1",
        source_type: "scenario",
        source_id: scenario.scenario_id,
        scenario_id: scenario.scenario_id,
        rule_code: "shared-device-ring",
        title: "Potential shared-device coordination ring",
        severity: scenario.baseline_risk,
        status: "investigating",
        narrative: "Scenario lead opened as a persistent case.",
        assigned_analyst_id: null,
        assigned_analyst_name: null,
        linked_case_id: "case-from-investigation-1",
        created_at: "2026-03-12T10:00:00",
        acknowledged_at: null,
        resolved_at: null,
      },
    ],
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
    mockedAddCaseComment.mockReset();
    mockedAnalyzeDataset.mockReset();
    mockedCreateCaseFromAnalysis.mockReset();
    mockedCreateCaseFromAlert.mockReset();
    mockedCreateCaseFromInvestigation.mockReset();
    mockedFetchAlerts.mockReset();
    mockedFetchAnalysisExplanation.mockReset();
    mockedFetchAnalysisResult.mockReset();
    mockedFetchAuditEvents.mockReset();
    mockedFetchCase.mockReset();
    mockedFetchCases.mockReset();
    mockedFetchCurrentOperator.mockReset();
    mockedFetchDatasets.mockReset();
    mockedFetchDashboardStats.mockReset();
    mockedFetchInvestigationClient.mockReset();
    mockedFetchScenarioCatalog.mockReset();
    mockedLoginOperator.mockReset();
    mockedUpdateCaseStatus.mockReset();

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
        completed_analyses: 0,
        high_risk_analyses: 0,
        workflow_stages: [],
        next_recommended_action: "Upload a dataset to start the primary workflow.",
      },
    });
    mockedFetchCases.mockResolvedValue({ cases: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchAlerts.mockResolvedValue({ alerts: [], total_count: 0, page: 1, page_size: 20 });
    mockedFetchDatasets.mockResolvedValue({ datasets: [] });
    mockedFetchAnalysisResult.mockResolvedValue(datasetAnalysisResponse);
    mockedFetchAnalysisExplanation.mockResolvedValue(datasetAnalysisExplanation);
    mockedFetchCase.mockResolvedValue(caseDetailFromAlertResponse);
    mockedCreateCaseFromAnalysis.mockResolvedValue({
      ...caseFromAnalysisResponse,
      analysis: datasetAnalysisResponse.analysis,
    });
    mockedCreateCaseFromAlert.mockResolvedValue(caseFromAlertResponse);
    mockedCreateCaseFromInvestigation.mockResolvedValue(
      buildCreateCaseFromInvestigationResponse(scenarios[0]),
    );
    mockedAddCaseComment.mockResolvedValue({});
    mockedUpdateCaseStatus.mockResolvedValue({});
  });

  it("renders runtime posture and requires operator sign-in", () => {
    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Relational Fraud Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Online").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByText("Start by uploading your transaction data.")).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByText("Development credentials")).toBeInTheDocument();
  });

  it("authenticates an analyst, filters scenarios, and loads a different investigation", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchInvestigationClient
      .mockResolvedValueOnce(buildInvestigationResponse(scenarios[0]))
      .mockResolvedValueOnce(buildInvestigationResponse(scenarios[1]));

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

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

    fireEvent.click(screen.getByRole("button", { name: /Scenarios/i }));
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

  it("creates a linked case from the scenario investigation view", async () => {
    const scenarioResponse = buildCreateCaseFromInvestigationResponse(scenarios[0]);

    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchInvestigationClient.mockResolvedValue(buildInvestigationResponse(scenarios[0]));
    mockedFetchAlerts
      .mockResolvedValueOnce(initialAlertList)
      .mockResolvedValueOnce({
        alerts: scenarioResponse.linked_alerts,
        total_count: 1,
        page: 1,
        page_size: 20,
      });
    mockedFetchCases
      .mockResolvedValueOnce({ cases: [], total_count: 0, page: 1, page_size: 20 })
      .mockResolvedValueOnce({
        cases: [scenarioResponse.case],
        total_count: 1,
        page: 1,
        page_size: 20,
      });

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Scenarios/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenarios/i }));
    fireEvent.click(screen.getByRole("button", { name: /synthetic identity gift card ring/i }));

    await waitFor(() => {
      expect(screen.getByText("Potential shared-device coordination ring")).toBeInTheDocument();
      expect(screen.getByText("RelationalAI Semantic Model")).toBeInTheDocument();
      expect(screen.getByText("shared-low-trust-devices")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Create linked case from investigation" }));

    await waitFor(() => {
      expect(mockedCreateCaseFromInvestigation).toHaveBeenCalledWith(
        "analyst-token",
        "synthetic-identity-ring",
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          "Synthetic Identity Gift Card Ring: Potential shared-device coordination ring",
        ),
      ).toBeInTheDocument();
    });
  });

  it("loads the audit trail for an admin session", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(adminPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchAuditEvents.mockResolvedValue({ events: auditEvents });

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

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
          completed_analyses: 0,
          high_risk_analyses: 0,
          workflow_stages: [],
          next_recommended_action:
            "Run analysis on newly uploaded datasets before the queue ages.",
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
          completed_analyses: 1,
          high_risk_analyses: 1,
          workflow_stages: [
            {
              stage_id: "upload",
              title: "Upload",
              description: "Datasets waiting to enter the scoring workflow.",
              total_count: 1,
              highlighted_count: 0,
              highlighted_label: "waiting for analysis",
            },
            {
              stage_id: "analyze",
              title: "Analyze",
              description:
                "Completed statistical and behavioral analyses over uploaded transaction data.",
              total_count: 1,
              highlighted_count: 1,
              highlighted_label: "high-risk analyses",
            },
            {
              stage_id: "alert",
              title: "Alert",
              description: "Alerts created from scored findings and triage thresholds.",
              total_count: 1,
              highlighted_count: 1,
              highlighted_label: "new alerts",
            },
            {
              stage_id: "case",
              title: "Case",
              description: "Persistent investigations opened from alerts or dataset reviews.",
              total_count: 0,
              highlighted_count: 0,
              highlighted_label: "open cases",
            },
          ],
          next_recommended_action:
            "Triage the new alert queue and link the highest-risk findings to cases.",
        },
      });
    mockedAnalyzeDataset.mockResolvedValue(datasetAnalysisResponse);

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

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

    fireEvent.click(screen.getAllByRole("button", { name: "Analyze Data" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Run analysis" }));

    await waitFor(() => {
      expect(mockedAnalyzeDataset).toHaveBeenCalledWith("admin-token", "dataset-1");
      expect(screen.getByText("Dataset analysis generated a high-risk alert candidate.")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockedFetchAnalysisExplanation).toHaveBeenCalledWith(
        "admin-token",
        "dataset-1",
        "admin",
      );
      expect(screen.getByText("AI Summary")).toBeInTheDocument();
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
  }, 15000);

  it("creates a case directly from the alert queue", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchDatasets
      .mockResolvedValueOnce(uploadedDatasetList)
      .mockResolvedValueOnce(completedDatasetList);
    mockedFetchAlerts
      .mockResolvedValueOnce(initialAlertList)
      .mockResolvedValueOnce(generatedAlertList)
      .mockResolvedValueOnce(linkedAlertList);
    mockedFetchCases
      .mockResolvedValueOnce({ cases: [], total_count: 0, page: 1, page_size: 20 })
      .mockResolvedValueOnce(caseFromAlertList);
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
          completed_analyses: 0,
          high_risk_analyses: 0,
          workflow_stages: [],
          next_recommended_action:
            "Run analysis on newly uploaded datasets before the queue ages.",
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
          completed_analyses: 1,
          high_risk_analyses: 1,
          workflow_stages: [],
          next_recommended_action:
            "Triage the new alert queue and link the highest-risk findings to cases.",
        },
      })
      .mockResolvedValueOnce({
        stats: {
          total_scenarios: 3,
          total_cases: 1,
          open_cases: 1,
          critical_cases: 0,
          total_alerts: 1,
          unacknowledged_alerts: 0,
          avg_risk_score: 68,
          cases_by_status: { open: 1 },
          alerts_by_severity: { high: 1 },
          recent_activity: [],
          risk_distribution: { high: 1 },
          total_datasets: 1,
          total_transactions_analyzed: 128,
          total_anomalies_found: 3,
          completed_analyses: 1,
          high_risk_analyses: 1,
          workflow_stages: [],
          next_recommended_action:
            "Work the open case and close the linked alert with a documented disposition.",
        },
      });
    mockedAnalyzeDataset.mockResolvedValue(datasetAnalysisResponse);

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedFetchDatasets).toHaveBeenCalledWith("analyst-token");
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Analyze Data" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Run analysis" }));

    await waitFor(() => {
      expect(mockedAnalyzeDataset).toHaveBeenCalledWith("analyst-token", "dataset-1");
    });

    fireEvent.click(screen.getByRole("button", { name: /Alerts/i }));

    await waitFor(() => {
      expect(screen.getByText("Velocity spike in dataset-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Create case" }));

    await waitFor(() => {
      expect(mockedCreateCaseFromAlert).toHaveBeenCalledWith("analyst-token", "alert-1");
    });

    await waitFor(() => {
      expect(screen.getAllByText("Alert review: Velocity spike in dataset-1").length).toBeGreaterThan(0);
      expect(screen.getByText("All Transactions")).toBeInTheDocument();
    });
  });

  it("creates a linked case from the analysis view", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchDatasets.mockResolvedValue(completedDatasetList);
    mockedFetchAlerts
      .mockResolvedValueOnce(generatedAlertList)
      .mockResolvedValueOnce(linkedAlertListFromAnalysis);
    mockedFetchCases
      .mockResolvedValueOnce({ cases: [], total_count: 0, page: 1, page_size: 20 })
      .mockResolvedValueOnce(caseFromAnalysisList);
    mockedFetchDashboardStats
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
          completed_analyses: 1,
          high_risk_analyses: 1,
          workflow_stages: [],
          next_recommended_action:
            "Create a case from the highest-risk dataset analysis so the review stays persistent.",
        },
      })
      .mockResolvedValueOnce({
        stats: {
          total_scenarios: 3,
          total_cases: 1,
          open_cases: 1,
          critical_cases: 0,
          total_alerts: 1,
          unacknowledged_alerts: 0,
          avg_risk_score: 68,
          cases_by_status: { open: 1 },
          alerts_by_severity: { high: 1 },
          recent_activity: [],
          risk_distribution: { high: 1 },
          total_datasets: 1,
          total_transactions_analyzed: 128,
          total_anomalies_found: 3,
          completed_analyses: 1,
          high_risk_analyses: 1,
          workflow_stages: [],
          next_recommended_action:
            "Advance open cases with comments, dispositions, or resolution notes.",
        },
      });

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(screen.getByText("Potential shared-device coordination ring")).toBeInTheDocument();
      expect(screen.getByText("Investigation Leads")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Create linked case from analysis" }));

    await waitFor(() => {
      expect(mockedCreateCaseFromAnalysis).toHaveBeenCalledWith("analyst-token", "dataset-1");
    });

    await waitFor(() => {
      expect(screen.getByText("march-transactions.csv: Potential shared-device coordination ring")).toBeInTheDocument();
    });
  });

  it("loads case detail with transactions and posts an analyst comment", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchCases
      .mockResolvedValueOnce(openCaseList)
      .mockResolvedValueOnce({
        cases: [{ ...caseFromAlertResponse.case, comment_count: 1 }],
        total_count: 1,
        page: 1,
        page_size: 20,
      });
    mockedFetchCase
      .mockResolvedValueOnce(caseDetailFromAlertResponse)
      .mockResolvedValueOnce(caseDetailWithCommentResponse);

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedFetchCases).toHaveBeenCalledWith("analyst-token");
    });

    fireEvent.click(screen.getByRole("button", { name: /Cases/i }));

    await waitFor(() => {
      expect(mockedFetchCase).toHaveBeenCalledWith("analyst-token", "case-from-alert-1");
      expect(screen.getByText("All Transactions")).toBeInTheDocument();
      expect(screen.getByText(/Global Travel Hub/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Add case comment"), {
      target: {
        value: "Reviewed the linked transactions and escalated the merchant/device overlap.",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Post comment" }));

    await waitFor(() => {
      expect(mockedAddCaseComment).toHaveBeenCalledWith(
        "analyst-token",
        "case-from-alert-1",
        "Reviewed the linked transactions and escalated the merchant/device overlap.",
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          "Reviewed the linked transactions and escalated the merchant/device overlap.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("resolves a case from the cases queue", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });
    mockedFetchCases
      .mockResolvedValueOnce(openCaseList)
      .mockResolvedValueOnce(resolvedCaseList);
    mockedFetchCase
      .mockResolvedValueOnce(caseDetailFromAlertResponse)
      .mockResolvedValueOnce(resolvedCaseDetailResponse);
    mockedFetchDashboardStats
      .mockResolvedValueOnce({
        stats: {
          total_scenarios: 3,
          total_cases: 1,
          open_cases: 1,
          critical_cases: 0,
          total_alerts: 0,
          unacknowledged_alerts: 0,
          avg_risk_score: 68,
          cases_by_status: { open: 1 },
          alerts_by_severity: {},
          recent_activity: [],
          risk_distribution: { high: 1 },
          total_datasets: 0,
          total_transactions_analyzed: 0,
          total_anomalies_found: 0,
          completed_analyses: 0,
          high_risk_analyses: 0,
          workflow_stages: [],
          next_recommended_action: "Resolve the active case once the disposition is confirmed.",
        },
      })
      .mockResolvedValueOnce({
        stats: {
          total_scenarios: 3,
          total_cases: 1,
          open_cases: 0,
          critical_cases: 0,
          total_alerts: 0,
          unacknowledged_alerts: 0,
          avg_risk_score: 68,
          cases_by_status: { resolved: 1 },
          alerts_by_severity: {},
          recent_activity: [],
          risk_distribution: { high: 1 },
          total_datasets: 0,
          total_transactions_analyzed: 0,
          total_anomalies_found: 0,
          completed_analyses: 0,
          high_risk_analyses: 0,
          workflow_stages: [],
          next_recommended_action: "Review the next case in queue.",
        },
      });

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(mockedFetchCases).toHaveBeenCalledWith("analyst-token");
    });

    fireEvent.click(screen.getByRole("button", { name: /Cases/i }));

    await waitFor(() => {
      expect(screen.getByText("Alert review: Velocity spike in dataset-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Resolve case" }));

    await waitFor(() => {
      expect(mockedUpdateCaseStatus).toHaveBeenCalledWith(
        "analyst-token",
        "case-from-alert-1",
        {
          status: "resolved",
          disposition: "confirmed-fraud",
        },
      );
    });

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Resolve case" }),
      ).not.toBeInTheDocument();
    });
  });

  it("displays a bootstrap error banner when the backend is unreachable", () => {
    render(
      <Dashboard
        backendHealth={null}
        bootstrapError="The backend is not reachable yet."
        workspaceGuide={null}
      />,
    );

    expect(screen.getByText("The backend is not reachable yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getAllByText("Offline").length).toBeGreaterThan(0);
  });

  it("shows humanized health status in the TopBar after sign-in", async () => {
    mockedLoginOperator.mockResolvedValue(buildLoginResponse(analystPrincipal));
    mockedFetchScenarioCatalog.mockResolvedValue({ scenarios });

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        workspaceGuide={workspaceGuide}
      />,
    );

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "analyst" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AnalystPassword123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);

    await waitFor(() => {
      expect(screen.getByText("Online")).toBeInTheDocument();
    });
  });
});
