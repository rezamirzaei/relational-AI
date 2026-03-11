"use client";

import { useDeferredValue, useMemo, useState, useTransition } from "react";

import { fetchInvestigationClient } from "@/lib/api";
import type { InvestigationResponse, ScenarioOverview } from "@/lib/contracts";

type DashboardProps = {
  initialScenarios: ScenarioOverview[];
  initialInvestigation: InvestigationResponse | null;
  bootstrapError: string | null;
};

const riskLevelOrder: Record<string, number> = {
  low: 24,
  medium: 48,
  high: 72,
  critical: 100,
};

export function Dashboard({
  initialScenarios,
  initialInvestigation,
  bootstrapError,
}: DashboardProps) {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(
    initialInvestigation?.investigation.scenario.scenario_id ?? initialScenarios[0]?.scenario_id ?? null,
  );
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(
    initialInvestigation,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(bootstrapError);
  const [isPending, beginTransition] = useTransition();
  const deferredSignals = useDeferredValue(investigation?.investigation.text_signals ?? []);

  const selectedScenario = useMemo(
    () =>
      initialScenarios.find((scenario) => scenario.scenario_id === selectedScenarioId) ??
      initialScenarios[0] ??
      null,
    [initialScenarios, selectedScenarioId],
  );

  function handleScenarioSelection(scenarioId: string) {
    setSelectedScenarioId(scenarioId);
    setErrorMessage(null);
    beginTransition(() => {
      void loadInvestigation(scenarioId);
    });
  }

  async function loadInvestigation(scenarioId: string) {
    try {
      const nextInvestigation = await fetchInvestigationClient(scenarioId);
      setInvestigation(nextInvestigation);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load investigation.");
    }
  }

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div className="eyebrow">Production Reference Architecture</div>
        <h1>Relational Fraud Intelligence</h1>
        <p className="hero-copy">
          A RelationalAI-ready fraud operations workspace with strict backend contracts,
          explainable rule hits, optional Hugging Face enrichment, and Docker-first delivery.
        </p>
        <div className="hero-band">
          <div>
            <span className="hero-label">Use case</span>
            <strong>Fraud detection and investigation orchestration</strong>
          </div>
          <div>
            <span className="hero-label">Patterns</span>
            <strong>Ports and adapters, strategy, fallback, assembler</strong>
          </div>
          <div>
            <span className="hero-label">Contract style</span>
            <strong>Object input and object output everywhere</strong>
          </div>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="surface scenario-rail">
          <div className="section-header">
            <span>Scenario Catalog</span>
            <span>{initialScenarios.length}</span>
          </div>
          {initialScenarios.map((scenario) => {
            const isSelected = scenario.scenario_id === selectedScenarioId;
            return (
              <button
                key={scenario.scenario_id}
                className={`scenario-card ${isSelected ? "selected" : ""}`}
                onClick={() => handleScenarioSelection(scenario.scenario_id)}
                type="button"
              >
                <div className="scenario-card-top">
                  <span className={`risk-chip ${scenario.baseline_risk}`}>{scenario.baseline_risk}</span>
                  <span className="scenario-industry">{scenario.industry}</span>
                </div>
                <h2>{scenario.title}</h2>
                <p>{scenario.summary}</p>
                <div className="scenario-footer">
                  <span>{scenario.transaction_count} txns</span>
                  <span>${scenario.total_volume.toLocaleString()}</span>
                </div>
              </button>
            );
          })}
        </aside>

        <section className="surface investigation-panel">
          {selectedScenario ? (
            <>
              <div className="section-header">
                <span>Active Investigation</span>
                <span>{isPending ? "Refreshing" : "Live"}</span>
              </div>
              <div className="headline-row">
                <div>
                  <h2>{selectedScenario.title}</h2>
                  <p className="muted-copy">{selectedScenario.hypothesis}</p>
                </div>
                {investigation ? (
                  <div className="risk-meter-shell">
                    <div className="risk-meter-label">
                      <span>Risk score</span>
                      <strong>{investigation.investigation.total_risk_score}/100</strong>
                    </div>
                    <div className="risk-meter-track">
                      <div
                        className={`risk-meter-fill ${investigation.investigation.risk_level}`}
                        style={{
                          width: `${riskLevelOrder[investigation.investigation.risk_level]}%`,
                        }}
                      />
                    </div>
                    <span className={`risk-chip ${investigation.investigation.risk_level}`}>
                      {investigation.investigation.risk_level}
                    </span>
                  </div>
                ) : null}
              </div>

              {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}

              {investigation ? (
                <>
                  <div className="metrics-grid">
                    <MetricCard
                      label="Suspicious volume"
                      value={`$${investigation.investigation.metrics.suspicious_transaction_volume.toLocaleString()}`}
                    />
                    <MetricCard
                      label="Shared devices"
                      value={String(investigation.investigation.metrics.shared_device_count)}
                    />
                    <MetricCard
                      label="Flagged transactions"
                      value={String(investigation.investigation.metrics.suspicious_transaction_count)}
                    />
                    <MetricCard
                      label="Linked customers"
                      value={String(investigation.investigation.metrics.linked_customer_count)}
                    />
                  </div>

                  <div className="content-grid">
                    <section className="content-card">
                      <div className="mini-header">
                        <span>Top Rule Hits</span>
                        <span>{investigation.investigation.top_rule_hits.length}</span>
                      </div>
                      <div className="stack">
                        {investigation.investigation.top_rule_hits.map((hit) => (
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
                        <span>Entity Graph</span>
                        <span>{investigation.investigation.graph_links.length}</span>
                      </div>
                      <div className="stack">
                        {investigation.investigation.graph_links.map((link, index) => (
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
                              <span className="weight-pill">
                                {(signal.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p>{signal.rationale}</p>
                            <span className="signal-meta">
                              {signal.provider} via {signal.source_kind}
                            </span>
                          </article>
                        ))}
                      </div>
                    </section>

                    <section className="content-card">
                      <div className="mini-header">
                        <span>Suspicious Transactions</span>
                        <span>{investigation.investigation.suspicious_transactions.length}</span>
                      </div>
                      <div className="stack">
                        {investigation.investigation.suspicious_transactions.map((transaction) => (
                          <article key={transaction.transaction_id} className="transaction-row">
                            <div>
                              <strong>{transaction.transaction_id}</strong>
                              <p>
                                {transaction.merchant_id} via {transaction.channel}
                              </p>
                            </div>
                            <div className="transaction-amount">
                              ${transaction.amount.toLocaleString()}
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  </div>

                  <div className="footer-grid">
                    <section className="content-card compact">
                      <div className="mini-header">
                        <span>Provider Summary</span>
                        <span>Runtime</span>
                      </div>
                      <div className="provider-grid">
                        <span>Reasoning</span>
                        <strong>
                          {investigation.investigation.provider_summary.active_reasoning_provider}
                        </strong>
                        <span>Text</span>
                        <strong>{investigation.investigation.provider_summary.active_text_provider}</strong>
                      </div>
                      <div className="stack">
                        {investigation.investigation.provider_summary.notes.map((note) => (
                          <p key={note} className="provider-note">
                            {note}
                          </p>
                        ))}
                      </div>
                    </section>

                    <section className="content-card compact">
                      <div className="mini-header">
                        <span>Recommended Actions</span>
                        <span>Queue</span>
                      </div>
                      <div className="stack">
                        {investigation.investigation.recommended_actions.map((action) => (
                          <p key={action} className="action-item">
                            {action}
                          </p>
                        ))}
                      </div>
                    </section>
                  </div>
                </>
              ) : (
                <div className="empty-state">
                  Start the backend and select a scenario to populate the workspace.
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">No scenarios are available yet.</div>
          )}
        </section>
      </section>
    </main>
  );
}

type MetricCardProps = {
  label: string;
  value: string;
};

function MetricCard({ label, value }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
