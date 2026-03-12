export type RiskLevel = "low" | "medium" | "high" | "critical";
export type OperatorRole = "admin" | "analyst";

export type ScenarioTag =
  | "fraud"
  | "synthetic-identity"
  | "account-takeover"
  | "device-ring"
  | "cross-border";

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

export type GraphLink = {
  relation: string;
  explanation: string;
  source: {
    entity_type: string;
    entity_id: string;
    display_name: string;
  };
  target: {
    entity_type: string;
    entity_id: string;
    display_name: string;
  };
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
  rate_limit_backend: string;
  seeded_scenarios: number;
  seeded_operators: number;
};
