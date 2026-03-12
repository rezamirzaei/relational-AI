"use client";

import { FormEvent, useDeferredValue, useEffect, useState, useTransition } from "react";

import {
  fetchAuditEvents,
  fetchCurrentOperator,
  fetchInvestigationClient,
  fetchScenarioCatalog,
  loginOperator,
} from "@/lib/api";
import type {
  AuditEvent,
  HealthResponse,
  InvestigationResponse,
  OperatorPrincipal,
  ScenarioOverview,
} from "@/lib/contracts";

type DashboardProps = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
};

const tokenStorageKey = "rfi.operator-token";
const riskMeterWidth: Record<string, number> = {
  low: 24,
  medium: 52,
  high: 76,
  critical: 100,
};

const currencyFormatter = new Intl.NumberFormat("en-US", {
  currency: "USD",
  maximumFractionDigits: 0,
  style: "currency",
});

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
});

export function Dashboard({ backendHealth, bootstrapError }: DashboardProps) {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [operator, setOperator] = useState<OperatorPrincipal | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioOverview[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("AnalystPassword123!");
  const [errorMessage, setErrorMessage] = useState<string | null>(bootstrapError);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isPending, startTransition] = useTransition();

  const deferredQuery = useDeferredValue(searchQuery);
  const deferredSignals = useDeferredValue(
    investigation?.investigation.text_signals ?? [],
  );
  const selectedScenario =
    scenarios.find((scenario) => scenario.scenario_id === selectedScenarioId) ??
    scenarios[0] ??
    null;
  const activeInvestigation = investigation?.investigation ?? null;
  const visibleScenarios = scenarios.filter((scenario) => {
    const query = deferredQuery.trim().toLowerCase();
    if (!query) {
      return true;
    }
    return [
      scenario.title,
      scenario.industry,
      scenario.summary,
      scenario.hypothesis,
      ...scenario.tags,
    ]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  useEffect(() => {
    const savedToken = window.localStorage.getItem(tokenStorageKey);
    if (!savedToken) {
      return;
    }
    void hydrateOperatorSession(savedToken);
  }, []);

  async function hydrateOperatorSession(token: string) {
    try {
      await loadWorkspace(token);
      setAuthToken(token);
      setLoginError(null);
    } catch (error) {
      window.localStorage.removeItem(tokenStorageKey);
      setAuthToken(null);
      setOperator(null);
      setScenarios([]);
      setInvestigation(null);
      setAuditEvents([]);
      setLoginError(
        error instanceof Error ? error.message : "Your session could not be restored.",
      );
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsAuthenticating(true);
    setLoginError(null);
    setErrorMessage(null);

    try {
      const result = await loginOperator(username, password);
      window.localStorage.setItem(tokenStorageKey, result.access_token);
      await loadWorkspace(result.access_token, result.principal);
      setAuthToken(result.access_token);
      setPassword("");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Could not sign in.");
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function loadWorkspace(
    token: string,
    knownPrincipal?: OperatorPrincipal,
  ): Promise<void> {
    const principal =
      knownPrincipal ?? (await fetchCurrentOperator(token)).principal;
    const scenarioCatalog = await fetchScenarioCatalog(token);
    const firstScenarioId = scenarioCatalog.scenarios[0]?.scenario_id ?? null;
    const nextInvestigation = firstScenarioId
      ? await fetchInvestigationClient(token, firstScenarioId)
      : null;
    const nextAuditEvents =
      principal.role === "admin" ? (await fetchAuditEvents(token)).events : [];

    setOperator(principal);
    setScenarios(scenarioCatalog.scenarios);
    setSelectedScenarioId(firstScenarioId);
    setInvestigation(nextInvestigation);
    setAuditEvents(nextAuditEvents);
  }

  async function handleScenarioSelection(scenarioId: string) {
    if (!authToken) {
      return;
    }
    setSelectedScenarioId(scenarioId);
    setErrorMessage(null);
    startTransition(() => {
      void loadInvestigation(authToken, scenarioId);
    });
  }

  async function loadInvestigation(token: string, scenarioId: string) {
    try {
      const nextInvestigation = await fetchInvestigationClient(token, scenarioId);
      setInvestigation(nextInvestigation);
      if (operator?.role === "admin") {
        setAuditEvents((await fetchAuditEvents(token)).events);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load investigation.",
      );
    }
  }

  function handleLogout() {
    window.localStorage.removeItem(tokenStorageKey);
    setAuthToken(null);
    setOperator(null);
    setScenarios([]);
    setSelectedScenarioId(null);
    setInvestigation(null);
    setAuditEvents([]);
    setLoginError(null);
    setErrorMessage(null);
    setPassword("");
  }

  return (
    <main className="page-shell">
      <header className="ops-header">
        <div>
          <div className="eyebrow">Fraud Operations Command</div>
          <h1>Relational Fraud Intelligence</h1>
        </div>
        <div className="status-row">
          <StatusPill
            label={backendHealth?.database_status ?? "offline"}
            tone={backendHealth?.database_status === "ready" ? "good" : "critical"}
          />
          <StatusPill
            label={backendHealth?.rate_limit_status ?? "unavailable"}
            tone={backendHealth?.rate_limit_status === "ready" ? "good" : "warning"}
          />
          <StatusPill
            label={operator?.role ?? "signed-out"}
            tone={operator ? "neutral" : "warning"}
          />
        </div>
      </header>

      <section className="hero-panel">
        <div className="hero-copy-block">
          <p className="hero-copy">
            A production-focused investigation workspace with operator authentication,
            audit logging, rate limiting, relational case storage, and explainable fraud
            reasoning. Analysts sign in before the platform exposes cases or evidence.
          </p>
          <div className="hero-ribbon">
            <span>JWT operator auth</span>
            <span>RBAC + audit trail</span>
            <span>Postgres and Redis ready</span>
          </div>
        </div>

        <div className="hero-stats">
          <article className="hero-stat-card">
            <span className="hero-label">Environment</span>
            <strong>{backendHealth?.environment ?? "offline"}</strong>
            <p>Runtime health exposed by the backend.</p>
          </article>
          <article className="hero-stat-card">
            <span className="hero-label">Seeded Cases</span>
            <strong>{backendHealth?.seeded_scenarios ?? 0}</strong>
            <p>Production-style relational investigations available after sign-in.</p>
          </article>
          <article className="hero-stat-card">
            <span className="hero-label">Operators</span>
            <strong>{backendHealth?.seeded_operators ?? 0}</strong>
            <p>Bootstrap operator count surfaced for secure environment bring-up.</p>
          </article>
        </div>
      </section>

      {!operator || !authToken ? (
        <section className="surface auth-shell">
          <div className="section-header">
            <span>Operator Sign-In</span>
            <span>Required</span>
          </div>
          <form className="auth-form" onSubmit={handleLogin}>
            <label className="auth-field">
              <span>Username</span>
              <input
                autoComplete="username"
                name="username"
                onChange={(event) => setUsername(event.target.value)}
                type="text"
                value={username}
              />
            </label>
            <label className="auth-field">
              <span>Password</span>
              <input
                autoComplete="current-password"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>
            <button className="primary-button" disabled={isAuthenticating} type="submit">
              {isAuthenticating ? "Signing in..." : "Sign in"}
            </button>
          </form>
          {loginError ? <div className="error-banner">{loginError}</div> : null}
          <div className="auth-help">
            <strong>Default demo operators</strong>
            <p>`analyst / AnalystPassword123!`</p>
            <p>`admin / AdminPassword123!`</p>
          </div>
        </section>
      ) : (
        <section className="workspace-grid">
          <aside className="surface scenario-rail">
            <div className="rail-toolbar">
              <div className="section-header">
                <span>Scenario Catalog</span>
                <span>{visibleScenarios.length}</span>
              </div>
              <div className="operator-banner">
                <div>
                  <span className="hero-label">Signed in</span>
                  <strong>{operator.display_name}</strong>
                </div>
                <button className="secondary-button" onClick={handleLogout} type="button">
                  Sign out
                </button>
              </div>
              <label className="search-shell">
                <span className="sr-only">Search scenarios</span>
                <input
                  aria-label="Search scenarios"
                  className="search-input"
                  onChange={(event) => setSearchQuery(event.target.value)}
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
                      onClick={() => handleScenarioSelection(scenario.scenario_id)}
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
                          <span key={tag} className="tag-pill">
                            {tag}
                          </span>
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
                <div className="empty-state">
                  No scenarios match that search. Try a tag like <code>cross-border</code>.
                </div>
              )}
            </div>
          </aside>

          <section className="surface investigation-panel">
            {selectedScenario && activeInvestigation ? (
              <>
                <div className="section-header">
                  <span>Active Investigation</span>
                  <span>{isPending ? "Refreshing evidence" : "Analyst view"}</span>
                </div>

                <div className="headline-row">
                  <div className="headline-copy">
                    <p className="eyebrow">Scenario hypothesis</p>
                    <h2>{selectedScenario.title}</h2>
                    <p className="muted-copy">{selectedScenario.hypothesis}</p>
                    <p className="summary-lead">{activeInvestigation.summary}</p>
                  </div>

                  <div className="risk-meter-shell">
                    <div className="risk-meter-label">
                      <span>Priority score</span>
                      <strong>{activeInvestigation.total_risk_score}/100</strong>
                    </div>
                    <div className="risk-meter-track">
                      <div
                        className={`risk-meter-fill ${activeInvestigation.risk_level}`}
                        style={{
                          width: `${riskMeterWidth[activeInvestigation.risk_level]}%`,
                        }}
                      />
                    </div>
                    <span className={`risk-chip ${activeInvestigation.risk_level}`}>
                      {activeInvestigation.risk_level}
                    </span>
                  </div>
                </div>

                {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}

                <div className="metrics-grid">
                  <MetricCard
                    label="Suspicious volume"
                    tone="critical"
                    value={currencyFormatter.format(
                      activeInvestigation.metrics.suspicious_transaction_volume,
                    )}
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
                  <MetricCard
                    label="Linked customers"
                    tone="good"
                    value={String(activeInvestigation.metrics.linked_customer_count)}
                  />
                </div>

                <div className="insight-grid">
                  <section className="content-card emphasis-card">
                    <div className="mini-header">
                      <span>Decision Summary</span>
                      <span>Queue this now</span>
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
                      <span>Runtime Posture</span>
                      <span>Platform</span>
                    </div>
                    <div className="provider-grid">
                      <span>Operator</span>
                      <strong>{operator.display_name}</strong>
                      <span>Role</span>
                      <strong>{operator.role}</strong>
                      <span>Database</span>
                      <strong>{backendHealth?.database_status ?? "unavailable"}</strong>
                      <span>Rate limit</span>
                      <strong>{backendHealth?.rate_limit_status ?? "unavailable"}</strong>
                      <span>Rate limit backend</span>
                      <strong>{backendHealth?.rate_limit_backend ?? "unavailable"}</strong>
                      <span>Reasoning</span>
                      <strong>
                        {activeInvestigation.provider_summary.active_reasoning_provider}
                      </strong>
                      <span>Text</span>
                      <strong>{activeInvestigation.provider_summary.active_text_provider}</strong>
                    </div>
                    <div className="stack">
                      {activeInvestigation.provider_summary.notes.map((note) => (
                        <p key={note} className="provider-note">
                          {note}
                        </p>
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
                      <span>Transaction Timeline</span>
                      <span>{activeInvestigation.suspicious_transactions.length}</span>
                    </div>
                    <div className="stack">
                      {activeInvestigation.suspicious_transactions.map((transaction) => (
                        <article key={transaction.transaction_id} className="transaction-row">
                          <div>
                            <strong>{transaction.transaction_id}</strong>
                            <p>
                              {transaction.merchant_id} via {transaction.channel}
                            </p>
                          </div>
                          <div className="transaction-meta">
                            <strong>{currencyFormatter.format(transaction.amount)}</strong>
                            <span>
                              {dateFormatter.format(new Date(transaction.occurred_at))}
                            </span>
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
                </div>

                {operator.role === "admin" ? (
                  <section className="content-card">
                    <div className="mini-header">
                      <span>Audit Trail</span>
                      <span>{auditEvents.length}</span>
                    </div>
                    <div className="stack">
                      {auditEvents.map((event) => (
                        <article key={event.event_id} className="transaction-row">
                          <div>
                            <strong>{event.action}</strong>
                            <p>
                              {event.actor_username ?? "anonymous"} on {event.path}
                            </p>
                          </div>
                          <div className="transaction-meta">
                            <strong>{event.status_code}</strong>
                            <span>
                              {dateFormatter.format(new Date(event.occurred_at))}
                            </span>
                          </div>
                        </article>
                      ))}
                    </div>
                  </section>
                ) : null}
              </>
            ) : (
              <div className="empty-state">
                Sign in and select a scenario to populate the workspace.
              </div>
            )}
          </section>
        </section>
      )}
    </main>
  );
}

type MetricCardProps = {
  label: string;
  tone: "critical" | "good" | "neutral" | "warning";
  value: string;
};

function MetricCard({ label, tone, value }: MetricCardProps) {
  return (
    <article className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

type StatusPillProps = {
  label: string;
  tone: "critical" | "good" | "neutral" | "warning";
};

function StatusPill({ label, tone }: StatusPillProps) {
  return <span className={`status-pill ${tone}`}>{label}</span>;
}
