"use client";

import { useMemo } from "react";

import { RiskGauge } from "@/components/charts";
import { MetricCard } from "@/components/dashboard-sections";
import type {
  FraudScenario,
  HealthResponse,
  InvestigationResponse,
  ScenarioOverview,
  TextSignal,
} from "@/lib/contracts";

function formatProviderName(provider: string): string {
  const lookup: Record<string, string> = {
    relationalai: "RelationalAI",
    "hybrid-relationalai": "Hybrid RelationalAI",
    "local-rule-engine": "Local rule engine",
    keyword: "Keyword",
    huggingface: "Hugging Face",
  };
  return lookup[provider] ?? provider;
}

function parseDraftScenario(draftScenarioJson: string): {
  scenario: FraudScenario | null;
  message: string;
} {
  try {
    const scenario = JSON.parse(draftScenarioJson) as FraudScenario;
    if (
      !scenario ||
      typeof scenario !== "object" ||
      !Array.isArray(scenario.transactions) ||
      !Array.isArray(scenario.customers)
    ) {
      return {
        scenario: null,
        message: "Draft JSON must contain scenario fields like customers and transactions.",
      };
    }
    return { scenario, message: "Draft scenario is ready to run." };
  } catch {
    return { scenario: null, message: "Draft JSON has a syntax error." };
  }
}

type InvestigateViewProps = {
  isPending: boolean;
  scenarios: ScenarioOverview[];
  selectedScenarioId: string | null;
  selectedScenario: ScenarioOverview | null;
  activeInvestigation: InvestigationResponse["investigation"] | null;
  activeInvestigationMatchesSelection: boolean;
  visibleScenarios: ScenarioOverview[];
  searchQuery: string;
  deferredSignals: TextSignal[];
  draftScenarioJson: string;
  draftScenarioError: string | null;
  activeInvestigationCanCreateCase: boolean;
  backendHealth: HealthResponse | null;
  currencyFormatter: Intl.NumberFormat;
  dateFormatter: Intl.DateTimeFormat;
  onSearchQueryChange: (query: string) => void;
  onDraftScenarioJsonChange: (json: string) => void;
  onScenarioSelection: (scenarioId: string) => void;
  onRunSelectedScenario: () => void;
  onRunDraftScenario: () => void;
  onLoadScenarioIntoDraft: () => void;
  onCreateCase: () => void;
};

export function InvestigateView({
  isPending,
  scenarios,
  selectedScenarioId,
  selectedScenario,
  activeInvestigation,
  activeInvestigationMatchesSelection,
  visibleScenarios,
  searchQuery,
  deferredSignals,
  draftScenarioJson,
  draftScenarioError,
  activeInvestigationCanCreateCase,
  backendHealth,
  currencyFormatter,
  dateFormatter,
  onSearchQueryChange,
  onDraftScenarioJsonChange,
  onScenarioSelection,
  onRunSelectedScenario,
  onRunDraftScenario,
  onLoadScenarioIntoDraft,
  onCreateCase,
}: InvestigateViewProps) {
  const reasoningProvider = activeInvestigation?.provider_summary.active_reasoning_provider ?? "";
  const isRelationalAIShowcaseActive = reasoningProvider.includes("relationalai");
  const semanticModel = activeInvestigation?.provider_summary.semantic_model ?? null;
  const externalQueryAugmentedFindingCount = semanticModel
    ? semanticModel.semantic_findings.filter(
        (finding) => finding.execution_mode === "external-query-augmented",
      ).length
    : 0;
  const activeInvestigationTitle = activeInvestigation?.scenario.title ?? selectedScenario?.title ?? "Scenario";
  const draftPreview = useMemo(() => parseDraftScenario(draftScenarioJson), [draftScenarioJson]);
  const isDraftInvestigationActive =
    activeInvestigation !== null && !activeInvestigationMatchesSelection && !activeInvestigationCanCreateCase;

  return (
    <section className="dashboard-view-stack">
      <section className="content-card overview-hero">
        <div>
          <p className="eyebrow">Investigations</p>
          <h2>Choose a library scenario or define your own draft, then run one clear investigation.</h2>
          <p className="muted-copy">
            This workspace is now organized around three steps: pick or draft a scenario,
            run the investigation, then review the highest-signal findings.
          </p>
        </div>
        <div className="metrics-grid" style={{ minWidth: 320 }}>
          <MetricCard label="Library scenarios" tone="neutral" value={String(scenarios.length)} />
          <MetricCard
            label="Draft transactions"
            tone={draftPreview.scenario?.transactions.length ? "warning" : "neutral"}
            value={String(draftPreview.scenario?.transactions.length ?? 0)}
          />
          <MetricCard
            label="Latest result"
            tone={activeInvestigation ? "critical" : "good"}
            value={activeInvestigation ? activeInvestigation.risk_level : "not run"}
          />
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="surface scenario-rail">
          <div className="rail-toolbar">
            <div className="section-header">
              <span>Scenario library</span>
              <span>{visibleScenarios.length}</span>
            </div>
            <label className="search-shell">
              <span className="sr-only">Search scenarios</span>
              <input
                aria-label="Search scenarios"
                className="search-input"
                onChange={(event) => onSearchQueryChange(event.target.value)}
                placeholder="Search title, tag, or summary"
                type="search"
                value={searchQuery}
              />
            </label>
          </div>
          <div className="scenario-list" data-testid="scenario-list">
            {visibleScenarios.length > 0 ? (
              visibleScenarios.map((scenario) => {
                const isSelected = scenario.scenario_id === selectedScenarioId;
                return (
                  <button
                    key={scenario.scenario_id}
                    className={`scenario-card ${isSelected ? "selected" : ""}`}
                    onClick={() => onScenarioSelection(scenario.scenario_id)}
                    type="button"
                  >
                    <div className="scenario-card-top">
                      <span className={`risk-chip ${scenario.baseline_risk}`}>{scenario.baseline_risk}</span>
                      <span className="scenario-industry">{scenario.industry}</span>
                    </div>
                    <h2>{scenario.title}</h2>
                    <p>{scenario.summary}</p>
                    <div className="tag-row">
                      {scenario.tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="tag-pill">{tag}</span>
                      ))}
                    </div>
                    <div className="scenario-footer">
                      <span>{scenario.transaction_count} transactions</span>
                      <span>{currencyFormatter.format(scenario.total_volume)}</span>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="empty-state">No scenarios match that search.</div>
            )}
          </div>
        </aside>

        <section className="surface investigation-panel">
          <div className="stack">
            <section className="content-card emphasis-card">
              <div className="mini-header">
                <span>1. Choose a scenario</span>
                <span>{selectedScenario ? "Selected" : "Pick one"}</span>
              </div>
              {selectedScenario ? (
                <div className="stack" style={{ marginTop: 12 }}>
                  <div className="signal-card">
                    <div className="signal-card-top">
                      <strong>{selectedScenario.title}</strong>
                      <span className={`risk-chip ${selectedScenario.baseline_risk}`}>{selectedScenario.baseline_risk}</span>
                    </div>
                    <p>{selectedScenario.summary}</p>
                    <span className="signal-meta">{selectedScenario.hypothesis}</span>
                    <span className="signal-meta">
                      {selectedScenario.transaction_count} transactions · {currencyFormatter.format(selectedScenario.total_volume)}
                    </span>
                  </div>
                  <div className="action-bar">
                    <button className="primary-button" onClick={onRunSelectedScenario} type="button">
                      Run selected scenario
                    </button>
                    <button className="secondary-button" onClick={onLoadScenarioIntoDraft} type="button">
                      Load selected scenario into draft editor
                    </button>
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  Select one library scenario to review its summary and run it.
                </div>
              )}
            </section>

            <section className="content-card">
              <div className="mini-header">
                <span>2. Define or edit a draft</span>
                <span>{draftPreview.scenario ? "Ready" : "Needs fixes"}</span>
              </div>
              <p className="provider-note" style={{ marginTop: 12 }}>
                Use this editor for ad hoc scenarios. Draft investigations run through the full
                engine, but they stay temporary and do not create linked cases automatically.
              </p>
              <div className="metrics-grid" style={{ marginTop: 12 }}>
                <MetricCard
                  label="Customers"
                  tone="neutral"
                  value={String(draftPreview.scenario?.customers.length ?? 0)}
                />
                <MetricCard
                  label="Transactions"
                  tone="warning"
                  value={String(draftPreview.scenario?.transactions.length ?? 0)}
                />
                <MetricCard
                  label="Devices"
                  tone="neutral"
                  value={String(draftPreview.scenario?.devices.length ?? 0)}
                />
                <MetricCard
                  label="Validation"
                  tone={draftPreview.scenario ? "good" : "critical"}
                  value={draftPreview.scenario ? "ready" : "invalid"}
                />
              </div>
              <label className="auth-field" style={{ marginTop: 12 }}>
                <span>Draft scenario JSON</span>
                <textarea
                  aria-label="Draft scenario JSON"
                  className="search-input"
                  data-testid="draft-scenario-json"
                  onChange={(event) => onDraftScenarioJsonChange(event.target.value)}
                  rows={18}
                  style={{ fontFamily: "monospace", minHeight: 320, resize: "vertical" }}
                  value={draftScenarioJson}
                />
              </label>
              <div className="stack" style={{ marginTop: 12 }}>
                <p className="provider-note">{draftScenarioError ?? draftPreview.message}</p>
                <div className="action-bar">
                  <button className="primary-button" onClick={onRunDraftScenario} type="button">
                    Run draft scenario
                  </button>
                </div>
              </div>
            </section>

            <section className="content-card emphasis-card">
              <div className="mini-header">
                <span>3. Review the result</span>
                <span>{isPending ? "Running..." : activeInvestigation ? "Available" : "Not run"}</span>
              </div>
              {!activeInvestigation ? (
                <div className="empty-state">
                  Run a selected or draft scenario to see a single investigation summary,
                  the main reasons it was flagged, and the operational status behind it.
                </div>
              ) : (
                <div className="stack" style={{ marginTop: 12 }}>
                  <div className="headline-row">
                    <div className="headline-copy">
                      <p className="eyebrow">
                        {isDraftInvestigationActive ? "Draft investigation" : "Active investigation"}
                      </p>
                      <h2>{activeInvestigationTitle}</h2>
                      <p className="summary-lead">{activeInvestigation.summary}</p>
                    </div>
                    <div className="risk-meter-shell">
                      <RiskGauge
                        score={activeInvestigation.total_risk_score}
                        level={activeInvestigation.risk_level}
                        label="Priority Score"
                      />
                    </div>
                  </div>

                  <div className="metrics-grid">
                    <MetricCard
                      label="Investigation leads"
                      tone={activeInvestigation.investigation_leads.length > 0 ? "critical" : "neutral"}
                      value={String(activeInvestigation.investigation_leads.length)}
                    />
                    <MetricCard
                      label="Suspicious volume"
                      tone="critical"
                      value={currencyFormatter.format(activeInvestigation.metrics.suspicious_transaction_volume)}
                    />
                    <MetricCard
                      label="Flagged transactions"
                      tone="warning"
                      value={String(activeInvestigation.metrics.suspicious_transaction_count)}
                    />
                    <MetricCard
                      label="Shared devices"
                      tone="neutral"
                      value={String(activeInvestigation.metrics.shared_device_count)}
                    />
                  </div>

                  <div className="action-bar">
                    <button
                      className="primary-button"
                      disabled={!activeInvestigationCanCreateCase}
                      onClick={onCreateCase}
                      type="button"
                    >
                      Create linked case from investigation
                    </button>
                  </div>
                  {!activeInvestigationCanCreateCase ? (
                    <p className="provider-note">
                      Draft investigations are temporary. Load them into the scenario catalog flow
                      before creating a linked case.
                    </p>
                  ) : null}

                  <div className="insight-grid">
                    <section className="content-card emphasis-card">
                      <div className="mini-header">
                        <span>Why it was flagged</span>
                        <span>
                          {activeInvestigation.investigation_leads.length + activeInvestigation.top_rule_hits.length}
                        </span>
                      </div>
                      <div className="stack" style={{ marginTop: 12 }}>
                        {activeInvestigation.investigation_leads.map((lead) => (
                          <article key={lead.lead_id} className="signal-card">
                            <div className="signal-card-top">
                              <strong>{lead.title}</strong>
                              <span className={`risk-chip ${lead.severity}`}>{lead.severity}</span>
                            </div>
                            <p>{lead.hypothesis}</p>
                            <p className="muted-copy">{lead.narrative}</p>
                          </article>
                        ))}
                        {activeInvestigation.top_rule_hits.map((hit) => (
                          <article key={hit.rule_code} className="signal-card">
                            <div className="signal-card-top">
                              <strong>{hit.title}</strong>
                              <span className="weight-pill">{hit.weight}</span>
                            </div>
                            <p>{hit.narrative}</p>
                          </article>
                        ))}
                        {activeInvestigation.investigation_leads.length === 0 &&
                        activeInvestigation.top_rule_hits.length === 0 ? (
                          <div className="empty-state">No major findings were generated.</div>
                        ) : null}
                      </div>
                    </section>

                    <section className="content-card emphasis-card">
                      <div className="mini-header">
                        <span>Next actions</span>
                        <span>{activeInvestigation.recommended_actions.length}</span>
                      </div>
                      <div className="action-stack" style={{ marginTop: 12 }}>
                        {activeInvestigation.recommended_actions.map((action) => (
                          <article key={action} className="action-item">
                            <span className="action-marker" />
                            <p>{action}</p>
                          </article>
                        ))}
                        {activeInvestigation.recommended_actions.length === 0 ? (
                          <div className="empty-state">No follow-up actions were generated.</div>
                        ) : null}
                      </div>
                    </section>

                    <section className="content-card">
                      <div className="mini-header">
                        <span>How it ran</span>
                        <span>Platform</span>
                      </div>
                      <div className="provider-grid" style={{ marginTop: 12 }}>
                        <span>Requested reasoning</span>
                        <strong>{formatProviderName(activeInvestigation.provider_summary.requested_reasoning_provider)}</strong>
                        <span>Active reasoning</span>
                        <strong>{formatProviderName(activeInvestigation.provider_summary.active_reasoning_provider)}</strong>
                        <span>Requested text analysis</span>
                        <strong>{formatProviderName(activeInvestigation.provider_summary.requested_text_provider)}</strong>
                        <span>Active text analysis</span>
                        <strong>{formatProviderName(activeInvestigation.provider_summary.active_text_provider)}</strong>
                        <span>Database</span>
                        <strong>{backendHealth?.database_status === "ready" ? "Ready" : "Unavailable"}</strong>
                        <span>Rate limiting</span>
                        <strong>{backendHealth?.rate_limit_status === "ready" ? "Ready" : "Degraded"}</strong>
                      </div>
                      <div className="stack" style={{ marginTop: 12 }}>
                        {isRelationalAIShowcaseActive ? (
                          <p className="provider-note">
                            RelationalAI showcase mode is active: deterministic rules stay the baseline,
                            while relational motifs amplify the investigation when the structure is suspicious.
                          </p>
                        ) : null}
                        {externalQueryAugmentedFindingCount > 0 ? (
                          <p className="provider-note">
                            Executed RelationalAI concept queries externally confirmed {externalQueryAugmentedFindingCount} promoted semantic finding{externalQueryAugmentedFindingCount === 1 ? "" : "s"}.
                          </p>
                        ) : null}
                        {activeInvestigation.provider_summary.notes.slice(0, 4).map((note) => (
                          <p key={note} className="provider-note">{note}</p>
                        ))}
                      </div>
                    </section>
                  </div>

                  {semanticModel ? (
                    <section className="content-card emphasis-card">
                      <div className="mini-header">
                        <span>RelationalAI Semantic Model</span>
                        <span>Drill-down</span>
                      </div>
                      <div className="metrics-grid" style={{ marginTop: 12 }}>
                        <MetricCard label="Rule packs" tone="neutral" value={String(semanticModel.active_rule_packs.length)} />
                        <MetricCard label="Semantic findings" tone={semanticModel.semantic_findings.length > 0 ? "critical" : "good"} value={String(semanticModel.semantic_findings.length)} />
                        <MetricCard label="Relationships" tone="neutral" value={String(semanticModel.relationship_names.length)} />
                        <MetricCard label="Seeded facts" tone="critical" value={String(semanticModel.seeded_fact_count)} />
                      </div>
                      <div className="stack" style={{ marginTop: 12 }}>
                        <p className="provider-note">{semanticModel.execution_posture}</p>
                        <div className="tag-row">
                          {semanticModel.active_rule_packs.map((rulePack) => (
                            <span key={rulePack} className="tag-pill">{rulePack}</span>
                          ))}
                        </div>
                        <div className="stack">
                          {semanticModel.query_blueprints.map((blueprint) => (
                            <article key={blueprint.code} className="signal-card">
                              <div className="signal-card-top">
                                <strong>{blueprint.code}</strong>
                                <span className="weight-pill">{blueprint.rule_pack}</span>
                              </div>
                              <p>{blueprint.description}</p>
                              {blueprint.derived_rule_paths.length > 0 ? (
                                <span className="signal-meta">
                                  {blueprint.derived_rule_paths.join(" -> ")}
                                </span>
                              ) : null}
                            </article>
                          ))}
                        </div>
                        <p className="eyebrow">Semantic findings</p>
                        <div className="stack">
                          {semanticModel.semantic_findings.map((finding) => (
                            <article key={finding.finding_id} className="signal-card">
                              <div className="signal-card-top">
                                <strong>{finding.title}</strong>
                                <span className="weight-pill">{finding.rule_pack}</span>
                              </div>
                              <p>{finding.narrative}</p>
                              <span className="signal-meta">
                                Confidence {(finding.confidence * 100).toFixed(0)}% · Risk +{finding.risk_contribution} · {finding.execution_mode}
                              </span>
                              {finding.derived_rule_path.length > 0 ? (
                                <span className="signal-meta">
                                  Rule path: {finding.derived_rule_path.join(" -> ")}
                                </span>
                              ) : null}
                            </article>
                          ))}
                          {semanticModel.semantic_findings.length === 0 ? (
                            <div className="empty-state">No semantic findings were promoted for this run.</div>
                          ) : null}
                        </div>
                      </div>
                    </section>
                  ) : null}

                  <div className="content-grid">
                    {activeInvestigation.suspicious_transactions.length > 0 ? (
                      <section className="content-card">
                        <div className="mini-header">
                          <span>Suspicious transactions</span>
                          <span>{activeInvestigation.suspicious_transactions.length}</span>
                        </div>
                        <div className="stack" style={{ marginTop: 12 }}>
                          {activeInvestigation.suspicious_transactions.map((txn) => (
                            <article key={txn.transaction_id} className="transaction-row">
                              <div>
                                <strong>{txn.transaction_id}</strong>
                                <p>{txn.merchant_id} via {txn.channel}</p>
                              </div>
                              <div className="transaction-meta">
                                <strong>{currencyFormatter.format(txn.amount)}</strong>
                                <span>{dateFormatter.format(new Date(txn.occurred_at))}</span>
                              </div>
                            </article>
                          ))}
                        </div>
                      </section>
                    ) : null}

                    {deferredSignals.length > 0 ? (
                      <section className="content-card">
                        <div className="mini-header">
                          <span>Text signals</span>
                          <span>{deferredSignals.length}</span>
                        </div>
                        <div className="stack" style={{ marginTop: 12 }}>
                          {deferredSignals.map((signal) => (
                            <article key={signal.signal_id} className="signal-card">
                              <div className="signal-card-top">
                                <strong>{signal.label}</strong>
                                <span className="weight-pill">{Math.round(signal.confidence * 100)}%</span>
                              </div>
                              <p>{signal.rationale}</p>
                            </article>
                          ))}
                        </div>
                      </section>
                    ) : null}

                    {activeInvestigation.graph_analysis ? (
                      <section className="content-card">
                        <div className="mini-header">
                          <span>Graph analysis</span>
                          <span>{activeInvestigation.graph_analysis.risk_amplification_factor}x</span>
                        </div>
                        <div className="metrics-grid" style={{ marginTop: 12 }}>
                          <MetricCard label="Components" tone="neutral" value={String(activeInvestigation.graph_analysis.connected_components)} />
                          <MetricCard label="Communities" tone="neutral" value={String(activeInvestigation.graph_analysis.community_count)} />
                          <MetricCard label="Density" tone="warning" value={activeInvestigation.graph_analysis.density.toFixed(3)} />
                          <MetricCard label="Risk amplifier" tone="critical" value={`${activeInvestigation.graph_analysis.risk_amplification_factor}x`} />
                        </div>
                      </section>
                    ) : null}
                  </div>
                </div>
              )}
            </section>
          </div>
        </section>
      </section>
    </section>
  );
}
