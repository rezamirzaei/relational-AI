"use client";

import { RiskGauge } from "@/components/charts";
import { MetricCard } from "@/components/dashboard-sections";
import type {
  HealthResponse,
  InvestigationResponse,
  ScenarioOverview,
  TextSignal,
} from "@/lib/contracts";

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
  backendHealth: HealthResponse | null;
  currencyFormatter: Intl.NumberFormat;
  dateFormatter: Intl.DateTimeFormat;
  onSearchQueryChange: (query: string) => void;
  onScenarioSelection: (scenarioId: string) => void;
  onCreateCase: () => void;
};

export function InvestigateView({
  isPending,
  selectedScenarioId,
  selectedScenario,
  activeInvestigation,
  activeInvestigationMatchesSelection,
  visibleScenarios,
  searchQuery,
  deferredSignals,
  backendHealth,
  currencyFormatter,
  dateFormatter,
  onSearchQueryChange,
  onScenarioSelection,
  onCreateCase,
}: InvestigateViewProps) {
  return (
    <section className="dashboard-view-stack">
      <section className="content-card overview-hero">
        <div>
          <p className="eyebrow">Fraud scenarios</p>
          <h2>Run structured fraud scenarios to surface investigation leads.</h2>
        </div>
        <div className="llm-note compact">
          <strong>How it works</strong>
          <p>
            Each scenario contains a set of realistic transactions. Select one to run
            the analysis engine, review generated leads, and decide whether to open a case.
          </p>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="surface scenario-rail">
          <div className="rail-toolbar">
            <div className="section-header">
              <span>Scenarios</span>
              <span>{visibleScenarios.length}</span>
            </div>
            <label className="search-shell">
              <span className="sr-only">Search scenarios</span>
              <input
                aria-label="Search scenarios"
                className="search-input"
                onChange={(event) => onSearchQueryChange(event.target.value)}
                placeholder="Search industry, tag, or narrative"
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
                      <span className={`risk-chip ${scenario.baseline_risk}`}>
                        {scenario.baseline_risk}
                      </span>
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
          {selectedScenario && activeInvestigation && activeInvestigationMatchesSelection ? (
            <>
              <div className="section-header">
                <span>Active Investigation</span>
                <span>{isPending ? "Loading..." : "Investigation results"}</span>
              </div>

              <div className="headline-row">
                <div className="headline-copy">
                  <p className="eyebrow">Scenario hypothesis</p>
                  <h2>{selectedScenario.title}</h2>
                  <p className="muted-copy">{selectedScenario.hypothesis}</p>
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
                <MetricCard label="Investigation leads" tone={activeInvestigation.investigation_leads.length > 0 ? "critical" : "neutral"} value={String(activeInvestigation.investigation_leads.length)} />
                <MetricCard label="Suspicious volume" tone="critical" value={currencyFormatter.format(activeInvestigation.metrics.suspicious_transaction_volume)} />
                <MetricCard label="Flagged transactions" tone="warning" value={String(activeInvestigation.metrics.suspicious_transaction_count)} />
                <MetricCard label="Shared devices" tone="neutral" value={String(activeInvestigation.metrics.shared_device_count)} />
                <MetricCard label="Linked customers" tone="warning" value={String(activeInvestigation.metrics.linked_customer_count)} />
              </div>

              {activeInvestigation.graph_analysis ? (
                <section className="content-card emphasis-card">
                  <div className="mini-header">
                    <span>Graph Analysis</span>
                    <span>Relationship network</span>
                  </div>
                  <div className="metrics-grid" style={{ marginTop: 12 }}>
                    <MetricCard label="Components" tone="neutral" value={String(activeInvestigation.graph_analysis.connected_components)} />
                    <MetricCard label="Density" tone={activeInvestigation.graph_analysis.density > 0.3 ? "warning" : "neutral"} value={activeInvestigation.graph_analysis.density.toFixed(3)} />
                    <MetricCard label="Communities" tone="neutral" value={String(activeInvestigation.graph_analysis.community_count)} />
                    <MetricCard label="Risk amplifier" tone={activeInvestigation.graph_analysis.risk_amplification_factor > 1.3 ? "critical" : "good"} value={`${activeInvestigation.graph_analysis.risk_amplification_factor}x`} />
                  </div>
                  {activeInvestigation.graph_analysis.hub_entities.length > 0 ? (
                    <div style={{ marginTop: 12 }}>
                      <p className="eyebrow" style={{ marginBottom: 8 }}>Hub entities</p>
                      <div className="tag-row">
                        {activeInvestigation.graph_analysis.hub_entities.map((hub) => (
                          <span key={hub.entity_id} className="tag-pill">
                            {hub.entity_type}: {hub.display_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </section>
              ) : null}

              <div className="action-bar">
                <button className="primary-button" onClick={onCreateCase} type="button">
                  Create linked case from investigation
                </button>
              </div>

              <div className="insight-grid">
                <section className="content-card emphasis-card">
                  <div className="mini-header">
                    <span>Investigation Leads</span>
                    <span>{activeInvestigation.investigation_leads.length}</span>
                  </div>
                  {activeInvestigation.investigation_leads.length > 0 ? (
                    <div className="stack">
                      {activeInvestigation.investigation_leads.map((lead) => (
                        <article key={lead.lead_id} className="signal-card">
                          <div className="signal-card-top">
                            <strong>{lead.title}</strong>
                            <span className={`risk-chip ${lead.severity}`}>{lead.severity}</span>
                          </div>
                          <p>{lead.hypothesis}</p>
                          <p className="muted-copy">{lead.narrative}</p>
                          {lead.entities.length > 0 ? (
                            <span className="signal-meta">
                              {lead.entities.slice(0, 4).map((entity) => entity.display_name).join(" · ")}
                            </span>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      No investigation leads were generated. Review the rule hits below for details.
                    </div>
                  )}
                </section>

                <section className="content-card emphasis-card">
                  <div className="mini-header">
                    <span>Recommended Actions</span>
                    <span>Next steps</span>
                  </div>
                  <div className="action-stack">
                    {activeInvestigation.recommended_actions.map((action) => (
                      <article key={action} className="action-item">
                        <span className="action-marker" />
                        <p>{action}</p>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="content-card">
                  <div className="mini-header">
                    <span>System Status</span>
                    <span>Platform</span>
                  </div>
                  <div className="provider-grid">
                    <span>Analysis engine</span>
                    <strong>{activeInvestigation.provider_summary.active_reasoning_provider ? "Active ✓" : "Unavailable"}</strong>
                    <span>Text analysis</span>
                    <strong>{activeInvestigation.provider_summary.active_text_provider ? "Active ✓" : "Unavailable"}</strong>
                    <span>Database</span>
                    <strong>{backendHealth?.database_status === "ready" ? "Ready ✓" : "Unavailable"}</strong>
                    <span>Rate limiting</span>
                    <strong>{backendHealth?.rate_limit_status === "ready" ? "Ready ✓" : "Degraded"}</strong>
                  </div>
                  <div className="stack">
                    {activeInvestigation.provider_summary.notes.map((note) => (
                      <p key={note} className="provider-note">{note}</p>
                    ))}
                  </div>
                </section>
              </div>

              <div className="content-grid">
                <section className="content-card">
                  <div className="mini-header">
                    <span>Top Rule Hits</span>
                    <span>{activeInvestigation.top_rule_hits.length}</span>
                  </div>
                  <div className="stack">
                    {activeInvestigation.top_rule_hits.map((hit) => (
                      <article key={hit.rule_code} className="signal-card">
                        <div className="signal-card-top">
                          <strong>{hit.title}</strong>
                          <span className="weight-pill">{hit.weight}</span>
                        </div>
                        <p>{hit.narrative}</p>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="content-card">
                  <div className="mini-header">
                    <span>Suspicious Transactions</span>
                    <span>{activeInvestigation.suspicious_transactions.length}</span>
                  </div>
                  <div className="stack">
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

                <section className="content-card">
                  <div className="mini-header">
                    <span>Entity Graph</span>
                    <span>{activeInvestigation.graph_links.length}</span>
                  </div>
                  <div className="stack">
                    {activeInvestigation.graph_links.map((link, index) => (
                      <article key={`${link.relation}-${index}`} className="graph-card">
                        <div className="graph-card-nodes">
                          <span>{link.source.display_name}</span>
                          <span className="graph-relation">{link.relation}</span>
                          <span>{link.target.display_name}</span>
                        </div>
                        <p>{link.explanation}</p>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="content-card">
                  <div className="mini-header">
                    <span>Text Signals</span>
                    <span>{deferredSignals.length}</span>
                  </div>
                  <div className="stack">
                    {deferredSignals.map((signal) => (
                      <article key={signal.signal_id} className="signal-card">
                        <div className="signal-card-top">
                          <strong>{signal.label}</strong>
                          <span className="weight-pill">{(signal.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <p>{signal.rationale}</p>
                      </article>
                    ))}
                  </div>
                </section>
              </div>
            </>
          ) : selectedScenario ? (
            <div className="empty-state">
              <p style={{ marginBottom: 12 }}>
                <strong>{selectedScenario.title}</strong>
              </p>
              <p className="muted-copy" style={{ marginBottom: 16 }}>
                {selectedScenario.summary}
              </p>
              <button
                className="primary-button"
                disabled={isPending}
                onClick={() => onScenarioSelection(selectedScenario.scenario_id)}
                type="button"
              >
                {isPending ? "Running investigation..." : "Run investigation"}
              </button>
            </div>
          ) : (
            <div className="empty-state">
              Select a scenario to run the investigation engine.
            </div>
          )}
        </section>
      </section>
    </section>
  );
}


