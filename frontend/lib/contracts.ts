export type RiskLevel = "low" | "medium" | "high" | "critical";
export type OperatorRole = "admin" | "analyst";
export type WorkflowSourceType = "scenario" | "dataset";
export type CaseStatus = "open" | "investigating" | "escalated" | "resolved" | "closed";
export type CasePriority = "low" | "medium" | "high" | "critical";
export type AlertStatus = "new" | "acknowledged" | "investigating" | "resolved" | "false-positive";
export type CaseDisposition = "confirmed-fraud" | "false-positive" | "inconclusive" | "referred-to-law-enforcement";
export type ExplanationAudience = "analyst" | "admin";

export type ScenarioTag =
  | "fraud"
  | "synthetic-identity"
  | "account-takeover"
  | "device-ring"
  | "cross-border"
  | "money-mule"
  | "bust-out"
  | "first-party";

export type ScenarioOverview = {
  scenario_id: string;
  title: string;
  industry: string;
  summary: string;
  hypothesis: string;
  tags: ScenarioTag[];
  transaction_count: number;
  total_volume: number;
  baseline_risk: RiskLevel;
};

export type RuleHit = {
  rule_code: string;
  title: string;
  weight: number;
  narrative: string;
};

export type EntityReference = {
  entity_type: string;
  entity_id: string;
  display_name: string;
};

export type GraphLink = {
  relation: string;
  explanation: string;
  source: EntityReference;
  target: EntityReference;
};

export type TextSignal = {
  signal_id: string;
  provider: string;
  source_kind: string;
  source_id: string;
  label: string;
  confidence: number;
  rationale: string;
};

export type TransactionRecord = {
  transaction_id: string;
  customer_id: string;
  account_id: string;
  device_id: string;
  merchant_id: string;
  occurred_at: string;
  amount: number;
  currency: string;
  channel: string;
  status: string;
};

export type GraphAnalysisResult = {
  connected_components: number;
  density: number;
  highest_degree_entity: EntityReference | null;
  highest_degree_score: number;
  community_count: number;
  shortest_path_length: number | null;
  hub_entities: EntityReference[];
  risk_amplification_factor: number;
};

export type InvestigationResponse = {
  investigation: {
    scenario: ScenarioOverview;
    risk_level: RiskLevel;
    total_risk_score: number;
    summary: string;
    metrics: {
      total_transaction_volume: number;
      suspicious_transaction_volume: number;
      suspicious_transaction_count: number;
      shared_device_count: number;
      linked_customer_count: number;
    };
    provider_summary: {
      requested_reasoning_provider: string;
      active_reasoning_provider: string;
      requested_text_provider: string;
      active_text_provider: string;
      notes: string[];
    };
    top_rule_hits: RuleHit[];
    graph_links: GraphLink[];
    text_signals: TextSignal[];
    suspicious_transactions: TransactionRecord[];
    recommended_actions: string[];
    graph_analysis: GraphAnalysisResult | null;
  };
};

export type ScenarioCatalogResponse = {
  scenarios: ScenarioOverview[];
};

export type OperatorPrincipal = {
  user_id: string;
  username: string;
  display_name: string;
  role: OperatorRole;
  is_active: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  principal: OperatorPrincipal;
};

export type CurrentOperatorResponse = {
  principal: OperatorPrincipal;
};

export type AuditEvent = {
  event_id: number;
  occurred_at: string;
  request_id: string;
  actor_user_id: string | null;
  actor_username: string | null;
  actor_role: OperatorRole | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  http_method: string;
  path: string;
  status_code: number;
  ip_address: string | null;
  user_agent: string | null;
  details: Record<string, string>;
};

export type AuditEventsResponse = {
  events: AuditEvent[];
};

export type HealthResponse = {
  status: "ok" | "degraded";
  app_name: string;
  environment: string;
  database_status: "ready" | "unavailable";
  rate_limit_status: "ready" | "degraded" | "unavailable";
  provider_status: "ready" | "degraded";
  rate_limit_backend: string;
  seeded_scenarios: number;
  seeded_operators: number;
  provider_posture: {
    requested_text_signal_provider: string;
    active_text_signal_provider: string;
    requested_reasoning_provider: string;
    active_reasoning_provider: string;
    requested_explanation_provider: string;
    active_explanation_provider: string;
    notes: string[];
  };
};

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

export type FraudCase = {
  case_id: string;
  source_type: WorkflowSourceType;
  source_id: string;
  scenario_id: string | null;
  title: string;
  status: CaseStatus;
  priority: CasePriority;
  assigned_analyst_id: string | null;
  assigned_analyst_name: string | null;
  risk_score: number;
  risk_level: RiskLevel;
  summary: string;
  disposition: CaseDisposition | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  sla_deadline: string | null;
  comment_count: number;
  alert_count: number;
};

export type CreateCaseResponse = {
  case: FraudCase;
};

export type ListCasesResponse = {
  cases: FraudCase[];
  total_count: number;
  page: number;
  page_size: number;
};

export type GetCaseResponse = {
  case: FraudCase;
};

export type CaseComment = {
  comment_id: string;
  case_id: string;
  author_id: string;
  author_name: string;
  body: string;
  created_at: string;
};

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export type FraudAlert = {
  alert_id: string;
  source_type: WorkflowSourceType;
  source_id: string;
  scenario_id: string | null;
  rule_code: string;
  title: string;
  severity: RiskLevel;
  status: AlertStatus;
  narrative: string;
  assigned_analyst_id: string | null;
  assigned_analyst_name: string | null;
  linked_case_id: string | null;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
};

export type ListAlertsResponse = {
  alerts: FraudAlert[];
  total_count: number;
  page: number;
  page_size: number;
};

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export type ActivityEvent = {
  event_type: string;
  description: string;
  actor: string | null;
  occurred_at: string;
  resource_id: string | null;
};

export type WorkflowStageSnapshot = {
  stage_id: string;
  title: string;
  description: string;
  total_count: number;
  highlighted_count: number;
  highlighted_label: string;
};

export type RoleStory = {
  story_id: string;
  persona_name: string;
  title: string;
  platform_role: OperatorRole;
  goal: string;
  workflow_steps: string[];
  success_signal: string;
  recommended_view: string;
};

export type WorkspaceGuide = {
  primary_workflow_title: string;
  primary_workflow_summary: string;
  role_stories: RoleStory[];
  scoring_guarantees: string[];
  llm_positioning_note: string;
};

export type ExplanationProviderSummary = {
  requested_provider: string;
  active_provider: string;
  source_of_truth: string;
  notes: string[];
};

export type DashboardStats = {
  total_scenarios: number;
  total_cases: number;
  open_cases: number;
  critical_cases: number;
  total_alerts: number;
  unacknowledged_alerts: number;
  avg_risk_score: number;
  cases_by_status: Record<string, number>;
  alerts_by_severity: Record<string, number>;
  recent_activity: ActivityEvent[];
  risk_distribution: Record<string, number>;
  total_datasets: number;
  total_transactions_analyzed: number;
  total_anomalies_found: number;
  completed_analyses: number;
  high_risk_analyses: number;
  workflow_stages: WorkflowStageSnapshot[];
  next_recommended_action: string;
};

export type DashboardStatsResponse = {
  stats: DashboardStats;
};

export type WorkspaceGuideResponse = {
  guide: WorkspaceGuide;
};

// ---------------------------------------------------------------------------
// Dataset & Analysis types
// ---------------------------------------------------------------------------

export type DatasetStatus = "uploaded" | "analyzing" | "completed" | "failed";

export type DatasetInfo = {
  dataset_id: string;
  name: string;
  uploaded_at: string;
  row_count: number;
  status: DatasetStatus;
  error_message: string | null;
};

export type DatasetListResponse = {
  datasets: DatasetInfo[];
};

export type BenfordDigit = {
  digit: number;
  expected_pct: number;
  actual_pct: number;
  deviation: number;
};

export type VelocitySpike = {
  entity_id: string;
  entity_type: string;
  window_start: string;
  window_end: string;
  transaction_count: number;
  total_amount: number;
  baseline_avg_count: number;
  z_score: number;
};

export type AnomalyFlag = {
  anomaly_id: string;
  anomaly_type: string;
  severity: RiskLevel;
  title: string;
  description: string;
  affected_entity_id: string;
  affected_entity_type: string;
  score: number;
  evidence: Record<string, unknown>;
};

export type AnalysisResultData = {
  analysis_id: string;
  dataset_id: string;
  completed_at: string;
  total_transactions: number;
  total_anomalies: number;
  risk_score: number;
  risk_level: RiskLevel;
  benford_chi_squared: number;
  benford_p_value: number;
  benford_is_suspicious: boolean;
  benford_digits: BenfordDigit[];
  outlier_count: number;
  outlier_pct: number;
  velocity_spikes: VelocitySpike[];
  graph_analysis: GraphAnalysisResult | null;
  anomalies: AnomalyFlag[];
  summary: string;
};

export type AnalysisResponse = {
  analysis: AnalysisResultData;
};

export type AnalysisExplanation = {
  dataset_id: string;
  dataset_name: string;
  audience: ExplanationAudience;
  headline: string;
  narrative: string;
  deterministic_evidence: string[];
  recommended_actions: string[];
  watchouts: string[];
  provider_summary: ExplanationProviderSummary;
};

export type AnalysisExplanationResponse = {
  explanation: AnalysisExplanation;
};
