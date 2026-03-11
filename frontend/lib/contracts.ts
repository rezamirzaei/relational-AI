export type RiskLevel = "low" | "medium" | "high" | "critical";

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
