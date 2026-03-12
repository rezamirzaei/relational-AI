"use client";

import { FormEvent, useDeferredValue, useEffect, useState, useTransition } from "react";

import {
  analyzeDataset,
  createCase,
  fetchAlerts,
  fetchAuditEvents,
  fetchCases,
  fetchCurrentOperator,
  fetchDashboardStats,
  fetchDatasets,
  fetchInvestigationClient,
  fetchScenarioCatalog,
  loginOperator,
  updateAlertStatus,
  updateCaseStatus,
  uploadDataset,
} from "@/lib/api";
import type {
  AnalysisResultData,
  AuditEvent,
  DashboardStats,
  DatasetInfo,
  FraudAlert,
  FraudCase,
  HealthResponse,
  InvestigationResponse,
  OperatorPrincipal,
  ScenarioOverview,
} from "@/lib/contracts";

type DashboardProps = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
};

type ActiveView = "overview" | "investigate" | "analyze" | "cases" | "alerts" | "audit";

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
  const [cases, setCases] = useState<FraudCase[]>([]);
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisResultData | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeView, setActiveView] = useState<ActiveView>("overview");
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
    if (!query) return true;
    return [scenario.title, scenario.industry, scenario.summary, scenario.hypothesis, ...scenario.tags]
      .join(" ").toLowerCase().includes(query);
  });

  useEffect(() => {
    const savedToken = window.localStorage.getItem(tokenStorageKey);
    if (!savedToken) return;
    void hydrateOperatorSession(savedToken);
  }, []);

  async function hydrateOperatorSession(token: string) {
    try {
      await loadWorkspace(token);
      setAuthToken(token);
      setLoginError(null);
    } catch {
      window.localStorage.removeItem(tokenStorageKey);
      setAuthToken(null);
      setOperator(null);
      setScenarios([]);
      setInvestigation(null);
      setAuditEvents([]);
      setCases([]);
      setAlerts([]);
      setDashboardStats(null);
      setLoginError("Your session could not be restored.");
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

  async function loadWorkspace(token: string, knownPrincipal?: OperatorPrincipal): Promise<void> {
    const principal = knownPrincipal ?? (await fetchCurrentOperator(token)).principal;
    const scenarioCatalog = await fetchScenarioCatalog(token);
    const firstScenarioId = scenarioCatalog.scenarios[0]?.scenario_id ?? null;
    const nextInvestigation = firstScenarioId
      ? await fetchInvestigationClient(token, firstScenarioId)
      : null;
    const nextAuditEvents = principal.role === "admin" ? (await fetchAuditEvents(token)).events : [];

    let nextStats: DashboardStats | null = null;
    let nextCases: FraudCase[] = [];
    let nextAlerts: FraudAlert[] = [];
    let nextDatasets: DatasetInfo[] = [];
    try {
      const [statsRes, casesRes, alertsRes, datasetsRes] = await Promise.all([
        fetchDashboardStats(token),
        fetchCases(token),
        fetchAlerts(token),
        fetchDatasets(token),
      ]);
      nextStats = statsRes.stats;
      nextCases = casesRes.cases;
      nextAlerts = alertsRes.alerts;
      nextDatasets = datasetsRes.datasets;
    } catch {
      // Non-critical — dashboard still works
    }

    setOperator(principal);
    setScenarios(scenarioCatalog.scenarios);
    setSelectedScenarioId(firstScenarioId);
    setInvestigation(nextInvestigation);
    setAuditEvents(nextAuditEvents);
    setDashboardStats(nextStats);
    setCases(nextCases);
    setAlerts(nextAlerts);
    setDatasets(nextDatasets);
  }

  async function handleScenarioSelection(scenarioId: string) {
    if (!authToken) return;
    setSelectedScenarioId(scenarioId);
    setActiveView("investigate");
    setErrorMessage(null);
    startTransition(() => { void loadInvestigation(authToken, scenarioId); });
  }

  async function loadInvestigation(token: string, scenarioId: string) {
    try {
      const nextInvestigation = await fetchInvestigationClient(token, scenarioId);
      setInvestigation(nextInvestigation);
      // Refresh alerts and stats after investigation (alerts auto-generated)
      try {
        const [alertsRes, statsRes] = await Promise.all([fetchAlerts(token), fetchDashboardStats(token)]);
        setAlerts(alertsRes.alerts);
        setDashboardStats(statsRes.stats);
      } catch { /* non-critical */ }
      if (operator?.role === "admin") {
        setAuditEvents((await fetchAuditEvents(token)).events);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load investigation.");
    }
  }

  async function handleCreateCase() {
    if (!authToken || !activeInvestigation) return;
    try {
      await createCase(authToken, {
        scenario_id: activeInvestigation.scenario.scenario_id,
        title: activeInvestigation.scenario.title,
        summary: activeInvestigation.summary,
        priority: activeInvestigation.risk_level,
      });
      const [casesRes, statsRes] = await Promise.all([fetchCases(authToken), fetchDashboardStats(authToken)]);
      setCases(casesRes.cases);
      setDashboardStats(statsRes.stats);
      setActiveView("cases");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create case.");
    }
  }

  async function handleAcknowledgeAlert(alertId: string) {
    if (!authToken) return;
    try {
      await updateAlertStatus(authToken, alertId, { status: "acknowledged" });
      const [alertsRes, statsRes] = await Promise.all([fetchAlerts(authToken), fetchDashboardStats(authToken)]);
      setAlerts(alertsRes.alerts);
      setDashboardStats(statsRes.stats);
    } catch { /* silent */ }
  }

  async function handleResolveCase(caseId: string) {
    if (!authToken) return;
    try {
      await updateCaseStatus(authToken, caseId, { status: "resolved", disposition: "confirmed-fraud" });
      const [casesRes, statsRes] = await Promise.all([fetchCases(authToken), fetchDashboardStats(authToken)]);
      setCases(casesRes.cases);
      setDashboardStats(statsRes.stats);
    } catch { /* silent */ }
  }

  async function handleUploadDataset(file: File) {
    if (!authToken) return;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      await uploadDataset(authToken, file);
      const datasetsRes = await fetchDatasets(authToken);
      setDatasets(datasetsRes.datasets);
      const statsRes = await fetchDashboardStats(authToken);
      setDashboardStats(statsRes.stats);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAnalyzeDataset(datasetId: string) {
    if (!authToken) return;
    setIsAnalyzing(true);
    setActiveAnalysis(null);
    setErrorMessage(null);
    try {
      const result = await analyzeDataset(authToken, datasetId);
      setActiveAnalysis(result.analysis);
      const [datasetsRes, statsRes] = await Promise.all([
        fetchDatasets(authToken),
        fetchDashboardStats(authToken),
      ]);
      setDatasets(datasetsRes.datasets);
      setDashboardStats(statsRes.stats);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Analysis failed.");
    } finally {
      setIsAnalyzing(false);
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
    setCases([]);
    setAlerts([]);
    setDashboardStats(null);
    setLoginError(null);
    setErrorMessage(null);
    setPassword("");
    setActiveView("overview");
  }

  return (
    <main className="page-shell">
      <header className="ops-header">
        <div>
          <div className="eyebrow">Fraud Operations Command Center</div>
          <h1>Relational Fraud Intelligence</h1>
        </div>
        <div className="status-row">
          <StatusPill label={backendHealth?.database_status ?? "offline"} tone={backendHealth?.database_status === "ready" ? "good" : "critical"} />
          <StatusPill label={backendHealth?.rate_limit_status ?? "unavailable"} tone={backendHealth?.rate_limit_status === "ready" ? "good" : "warning"} />
          <StatusPill label={operator?.role ?? "signed-out"} tone={operator ? "neutral" : "warning"} />
        </div>
      </header>

      {!operator || !authToken ? (
        <>
          <section className="hero-panel">
            <div className="hero-copy-block">
              <p className="hero-copy">
                Upload your own transaction data and detect fraud automatically using Benford&apos;s Law,
                statistical outlier detection, velocity spike analysis, and round-amount structuring detection.
                Investigate pre-built scenarios, manage cases, and track alerts — all in one platform.
              </p>
              <div className="hero-ribbon">
                <span>CSV data upload</span>
                <span>Benford&apos;s Law</span>
                <span>Anomaly detection</span>
                <span>Case management</span>
              </div>
            </div>
            <div className="hero-stats">
              <article className="hero-stat-card">
                <span className="hero-label">Environment</span>
                <strong>{backendHealth?.environment ?? "offline"}</strong>
                <p>Runtime health exposed by the backend.</p>
              </article>
              <article className="hero-stat-card">
                <span className="hero-label">Scenarios</span>
                <strong>{backendHealth?.seeded_scenarios ?? 0}</strong>
                <p>Relational fraud investigations available.</p>
              </article>
              <article className="hero-stat-card">
                <span className="hero-label">Operators</span>
                <strong>{backendHealth?.seeded_operators ?? 0}</strong>
                <p>Bootstrap operator accounts.</p>
              </article>
            </div>
          </section>

          <section className="surface auth-shell">
            <div className="section-header"><span>Operator Sign-In</span><span>Required</span></div>
            <form className="auth-form" onSubmit={handleLogin}>
              <label className="auth-field">
                <span>Username</span>
                <input autoComplete="username" name="username" onChange={(e) => setUsername(e.target.value)} type="text" value={username} />
              </label>
              <label className="auth-field">
                <span>Password</span>
                <input autoComplete="current-password" name="password" onChange={(e) => setPassword(e.target.value)} type="password" value={password} />
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
        </>
      ) : (
        <>
          {/* Navigation bar */}
          <nav className="nav-bar">
            <div className="nav-left">
              {(["overview", "investigate", "analyze", "cases", "alerts", ...(operator.role === "admin" ? ["audit"] : [])] as ActiveView[]).map((view) => (
                <button
                  key={view}
                  className={`nav-tab ${activeView === view ? "active" : ""}`}
                  onClick={() => setActiveView(view)}
                  type="button"
                >
                  {view === "overview" ? "Dashboard" : view === "investigate" ? "Investigate" : view === "analyze" ? "Analyze Data" : view === "audit" ? "Audit Trail" : view.charAt(0).toUpperCase() + view.slice(1)}
                  {view === "alerts" && alerts.filter(a => a.status === "new").length > 0 && (
                    <span className="nav-badge">{alerts.filter(a => a.status === "new").length}</span>
                  )}
                  {view === "cases" && cases.filter(c => c.status === "open" || c.status === "investigating").length > 0 && (
                    <span className="nav-badge">{cases.filter(c => c.status === "open" || c.status === "investigating").length}</span>
                  )}
                </button>
              ))}
            </div>
            <div className="nav-right">
              <span className="operator-info">{operator.display_name} ({operator.role})</span>
              <button className="secondary-button" onClick={handleLogout} type="button">Sign out</button>
            </div>
          </nav>

          {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}

          {/* ======= OVERVIEW ======= */}
          {activeView === "overview" && (
            <section className="dashboard-overview">
              <div className="stats-grid">
                <MetricCard label="Total Scenarios" value={String(dashboardStats?.total_scenarios ?? scenarios.length)} tone="neutral" />
                <MetricCard label="Datasets Uploaded" value={String(dashboardStats?.total_datasets ?? datasets.length)} tone="neutral" />
                <MetricCard label="Transactions Analyzed" value={(dashboardStats?.total_transactions_analyzed ?? 0).toLocaleString()} tone="neutral" />
                <MetricCard label="Anomalies Found" value={String(dashboardStats?.total_anomalies_found ?? 0)} tone={dashboardStats?.total_anomalies_found ? "critical" : "neutral"} />
                <MetricCard label="Active Cases" value={String(dashboardStats?.open_cases ?? 0)} tone="warning" />
                <MetricCard label="Pending Alerts" value={String(dashboardStats?.unacknowledged_alerts ?? 0)} tone="critical" />
                <MetricCard label="Total Cases" value={String(dashboardStats?.total_cases ?? 0)} tone="neutral" />
                <MetricCard label="Avg Risk Score" value={`${dashboardStats?.avg_risk_score?.toFixed(0) ?? 0}/100`} tone="warning" />
              </div>

              {dashboardStats && Object.keys(dashboardStats.cases_by_status).length > 0 && (
                <div className="insight-grid">
                  <section className="content-card">
                    <div className="mini-header"><span>Cases by Status</span><span>{dashboardStats.total_cases}</span></div>
                    <div className="bar-chart">
                      {Object.entries(dashboardStats.cases_by_status).map(([status, count]) => (
                        <div key={status} className="bar-row">
                          <span className="bar-label">{status}</span>
                          <div className="bar-track">
                            <div className={`bar-fill ${status === "open" || status === "investigating" ? "warning" : "good"}`} style={{ width: `${Math.max(8, (count / Math.max(1, dashboardStats.total_cases)) * 100)}%` }} />
                          </div>
                          <span className="bar-value">{count}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                  <section className="content-card">
                    <div className="mini-header"><span>Alerts by Severity</span><span>{dashboardStats.total_alerts}</span></div>
                    <div className="bar-chart">
                      {Object.entries(dashboardStats.alerts_by_severity).map(([severity, count]) => (
                        <div key={severity} className="bar-row">
                          <span className="bar-label">{severity}</span>
                          <div className="bar-track">
                            <div className={`bar-fill ${severity}`} style={{ width: `${Math.max(8, (count / Math.max(1, dashboardStats.total_alerts)) * 100)}%` }} />
                          </div>
                          <span className="bar-value">{count}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                </div>
              )}

              {dashboardStats?.recent_activity && dashboardStats.recent_activity.length > 0 && (
                <section className="content-card">
                  <div className="mini-header"><span>Recent Activity</span><span>{dashboardStats.recent_activity.length}</span></div>
                  <div className="stack">
                    {dashboardStats.recent_activity.map((event, i) => (
                      <article key={i} className="transaction-row">
                        <div>
                          <strong>{event.event_type}</strong>
                          <p>{event.description}</p>
                        </div>
                        <div className="transaction-meta">
                          <span>{dateFormatter.format(new Date(event.occurred_at))}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              )}

              {(!dashboardStats || dashboardStats.total_cases === 0) && (
                <section className="content-card emphasis-card">
                  <div className="mini-header"><span>Getting Started</span><span>Guide</span></div>
                  <div className="action-stack">
                    <article className="action-item"><span className="action-marker" /><p>Go to <strong>Investigate</strong> to run fraud analysis on a scenario.</p></article>
                    <article className="action-item"><span className="action-marker" /><p>When a high-risk investigation completes, <strong>alerts are auto-generated</strong>.</p></article>
                    <article className="action-item"><span className="action-marker" /><p>Create a <strong>case</strong> from the investigation to track and resolve it.</p></article>
                    <article className="action-item"><span className="action-marker" /><p>Manage alert and case queues from the <strong>Cases</strong> and <strong>Alerts</strong> tabs.</p></article>
                  </div>
                </section>
              )}
            </section>
          )}

          {/* ======= INVESTIGATE ======= */}
          {activeView === "investigate" && (
            <section className="workspace-grid">
              <aside className="surface scenario-rail">
                <div className="rail-toolbar">
                  <div className="section-header"><span>Scenario Catalog</span><span>{visibleScenarios.length}</span></div>
                  <label className="search-shell">
                    <span className="sr-only">Search scenarios</span>
                    <input aria-label="Search scenarios" className="search-input" onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search industry, tag, or narrative" type="search" value={searchQuery} />
                  </label>
                </div>
                <div className="scenario-list" data-testid="scenario-list">
                  {visibleScenarios.length > 0 ? visibleScenarios.map((scenario) => {
                    const isSelected = scenario.scenario_id === selectedScenarioId;
                    return (
                      <button key={scenario.scenario_id} className={`scenario-card ${isSelected ? "selected" : ""}`} onClick={() => handleScenarioSelection(scenario.scenario_id)} type="button">
                        <div className="scenario-card-top">
                          <span className={`risk-chip ${scenario.baseline_risk}`}>{scenario.baseline_risk}</span>
                          <span className="scenario-industry">{scenario.industry}</span>
                        </div>
                        <h2>{scenario.title}</h2>
                        <p>{scenario.summary}</p>
                        <div className="tag-row">
                          {scenario.tags.slice(0, 3).map((tag) => (<span key={tag} className="tag-pill">{tag}</span>))}
                        </div>
                        <div className="scenario-footer">
                          <span>{scenario.transaction_count} transactions</span>
                          <span>{currencyFormatter.format(scenario.total_volume)}</span>
                        </div>
                      </button>
                    );
                  }) : (
                    <div className="empty-state">No scenarios match that search.</div>
                  )}
                </div>
              </aside>

              <section className="surface investigation-panel">
                {selectedScenario && activeInvestigation ? (
                  <>
                    <div className="section-header">
                      <span>Active Investigation</span>
                      <span>{isPending ? "Refreshing evidence..." : "Analyst view"}</span>
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
                          <div className={`risk-meter-fill ${activeInvestigation.risk_level}`} style={{ width: `${riskMeterWidth[activeInvestigation.risk_level]}%` }} />
                        </div>
                        <span className={`risk-chip ${activeInvestigation.risk_level}`}>{activeInvestigation.risk_level}</span>
                      </div>
                    </div>

                    <div className="metrics-grid">
                      <MetricCard label="Suspicious volume" tone="critical" value={currencyFormatter.format(activeInvestigation.metrics.suspicious_transaction_volume)} />
                      <MetricCard label="Flagged transactions" tone="warning" value={String(activeInvestigation.metrics.suspicious_transaction_count)} />
                      <MetricCard label="Shared devices" tone="neutral" value={String(activeInvestigation.metrics.shared_device_count)} />
                      <MetricCard label="Linked customers" tone="good" value={String(activeInvestigation.metrics.linked_customer_count)} />
                    </div>

                    {/* Graph Analysis Card */}
                    {activeInvestigation.graph_analysis && (
                      <section className="content-card emphasis-card">
                        <div className="mini-header"><span>Graph Analysis</span><span>Relationship network</span></div>
                        <div className="metrics-grid" style={{ marginTop: 12 }}>
                          <MetricCard label="Components" tone="neutral" value={String(activeInvestigation.graph_analysis.connected_components)} />
                          <MetricCard label="Density" tone={activeInvestigation.graph_analysis.density > 0.3 ? "warning" : "neutral"} value={activeInvestigation.graph_analysis.density.toFixed(3)} />
                          <MetricCard label="Communities" tone="neutral" value={String(activeInvestigation.graph_analysis.community_count)} />
                          <MetricCard label="Risk amplifier" tone={activeInvestigation.graph_analysis.risk_amplification_factor > 1.3 ? "critical" : "good"} value={`${activeInvestigation.graph_analysis.risk_amplification_factor}x`} />
                        </div>
                        {activeInvestigation.graph_analysis.hub_entities.length > 0 && (
                          <div style={{ marginTop: 12 }}>
                            <p className="eyebrow" style={{ marginBottom: 8 }}>Hub entities (highest connectivity)</p>
                            <div className="tag-row">
                              {activeInvestigation.graph_analysis.hub_entities.map((hub) => (
                                <span key={hub.entity_id} className="tag-pill">{hub.entity_type}: {hub.display_name}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </section>
                    )}

                    {/* Action bar */}
                    <div className="action-bar">
                      <button className="primary-button" onClick={handleCreateCase} type="button">
                        Create case from investigation
                      </button>
                    </div>

                    <div className="insight-grid">
                      <section className="content-card emphasis-card">
                        <div className="mini-header"><span>Recommended Actions</span><span>Queue this now</span></div>
                        <div className="action-stack">
                          {activeInvestigation.recommended_actions.map((action) => (
                            <article key={action} className="action-item"><span className="action-marker" /><p>{action}</p></article>
                          ))}
                        </div>
                      </section>
                      <section className="content-card">
                        <div className="mini-header"><span>Runtime Posture</span><span>Platform</span></div>
                        <div className="provider-grid">
                          <span>Reasoning</span><strong>{activeInvestigation.provider_summary.active_reasoning_provider}</strong>
                          <span>Text</span><strong>{activeInvestigation.provider_summary.active_text_provider}</strong>
                          <span>Database</span><strong>{backendHealth?.database_status ?? "unavailable"}</strong>
                          <span>Rate limit</span><strong>{backendHealth?.rate_limit_backend ?? "unavailable"}</strong>
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
                        <div className="mini-header"><span>Top Rule Hits</span><span>{activeInvestigation.top_rule_hits.length}</span></div>
                        <div className="stack">
                          {activeInvestigation.top_rule_hits.map((hit) => (
                            <article key={hit.rule_code} className="signal-card">
                              <div className="signal-card-top"><strong>{hit.title}</strong><span className="weight-pill">{hit.weight}</span></div>
                              <p>{hit.narrative}</p>
                            </article>
                          ))}
                        </div>
                      </section>

                      <section className="content-card">
                        <div className="mini-header"><span>Suspicious Transactions</span><span>{activeInvestigation.suspicious_transactions.length}</span></div>
                        <div className="stack">
                          {activeInvestigation.suspicious_transactions.map((txn) => (
                            <article key={txn.transaction_id} className="transaction-row">
                              <div><strong>{txn.transaction_id}</strong><p>{txn.merchant_id} via {txn.channel}</p></div>
                              <div className="transaction-meta">
                                <strong>{currencyFormatter.format(txn.amount)}</strong>
                                <span>{dateFormatter.format(new Date(txn.occurred_at))}</span>
                              </div>
                            </article>
                          ))}
                        </div>
                      </section>

                      <section className="content-card">
                        <div className="mini-header"><span>Entity Graph</span><span>{activeInvestigation.graph_links.length}</span></div>
                        <div className="stack">
                          {activeInvestigation.graph_links.map((link, i) => (
                            <article key={`${link.relation}-${i}`} className="graph-card">
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
                        <div className="mini-header"><span>Text Signals</span><span>{deferredSignals.length}</span></div>
                        <div className="stack">
                          {deferredSignals.map((signal) => (
                            <article key={signal.signal_id} className="signal-card">
                              <div className="signal-card-top"><strong>{signal.label}</strong><span className="weight-pill">{(signal.confidence * 100).toFixed(0)}%</span></div>
                              <p>{signal.rationale}</p>
                              <span className="signal-meta">{signal.provider} via {signal.source_kind}</span>
                            </article>
                          ))}
                        </div>
                      </section>
                    </div>
                  </>
                ) : (
                  <div className="empty-state">Select a scenario to begin an investigation.</div>
                )}
              </section>
            </section>
          )}

          {/* ======= ANALYZE DATA ======= */}
          {activeView === "analyze" && (
            <section className="surface" style={{ padding: 24 }}>
              <div className="section-header"><span>Transaction Data Analysis</span><span>{datasets.length} datasets</span></div>

              {/* Upload area */}
              <div className="upload-zone">
                <p><strong>Upload a transaction CSV</strong></p>
                <p className="muted-copy">
                  Required columns: <code>transaction_id</code>, <code>account_id</code>, <code>amount</code>, <code>timestamp</code><br />
                  Optional: <code>merchant</code>, <code>category</code>, <code>device_fingerprint</code>, <code>ip_country</code>, <code>channel</code>, <code>is_fraud</code>
                </p>
                <input
                  type="file"
                  accept=".csv"
                  disabled={isUploading}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleUploadDataset(f);
                    e.target.value = "";
                  }}
                />
                {isUploading && <p className="muted-copy">Uploading...</p>}
                <p className="muted-copy" style={{ marginTop: 8 }}>
                  Try our <a href="https://github.com" target="_blank" rel="noopener">sample_transactions.csv</a> from <code>docs/sample_data/</code>
                </p>
              </div>

              {/* Dataset list */}
              {datasets.length > 0 && (
                <div className="stack" style={{ marginTop: 20 }}>
                  <h3>Uploaded Datasets</h3>
                  {datasets.map((ds) => (
                    <article key={ds.dataset_id} className="case-card">
                      <div className="case-card-header">
                        <div>
                          <span className={`status-chip ${ds.status === "completed" ? "resolved" : ds.status === "failed" ? "escalated" : "open"}`}>
                            {ds.status}
                          </span>
                          <strong>{ds.name}</strong>
                        </div>
                        <span className="case-date">{dateFormatter.format(new Date(ds.uploaded_at))}</span>
                      </div>
                      <p className="muted-copy">{ds.row_count.toLocaleString()} transactions</p>
                      {ds.error_message && <div className="error-banner">{ds.error_message}</div>}
                      <div className="case-card-footer">
                        {ds.status === "uploaded" && (
                          <button className="primary-button" disabled={isAnalyzing} onClick={() => handleAnalyzeDataset(ds.dataset_id)} type="button">
                            {isAnalyzing ? "Analyzing..." : "🔍 Run Fraud Analysis"}
                          </button>
                        )}
                        {ds.status === "completed" && (
                          <button className="secondary-button" onClick={() => handleAnalyzeDataset(ds.dataset_id)} type="button">
                            Re-analyze
                          </button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}

              {/* Analysis results */}
              {activeAnalysis && (
                <div className="analysis-results" style={{ marginTop: 24 }}>
                  <div className="section-header">
                    <span>Analysis Results</span>
                    <span className={`risk-chip ${activeAnalysis.risk_level}`}>
                      Risk: {activeAnalysis.risk_score}/100 ({activeAnalysis.risk_level})
                    </span>
                  </div>

                  <p style={{ margin: "12px 0", lineHeight: 1.6 }}>{activeAnalysis.summary}</p>

                  {/* Summary metrics */}
                  <div className="stats-grid">
                    <MetricCard label="Transactions Analyzed" value={activeAnalysis.total_transactions.toLocaleString()} tone="neutral" />
                    <MetricCard label="Anomalies Detected" value={String(activeAnalysis.total_anomalies)} tone={activeAnalysis.total_anomalies > 0 ? "critical" : "neutral"} />
                    <MetricCard label="Statistical Outliers" value={`${activeAnalysis.outlier_count} (${activeAnalysis.outlier_pct}%)`} tone={activeAnalysis.outlier_count > 0 ? "warning" : "neutral"} />
                    <MetricCard label="Velocity Spikes" value={String(activeAnalysis.velocity_spikes.length)} tone={activeAnalysis.velocity_spikes.length > 0 ? "warning" : "neutral"} />
                    <MetricCard label="Benford p-value" value={activeAnalysis.benford_p_value.toFixed(4)} tone={activeAnalysis.benford_is_suspicious ? "critical" : "neutral"} />
                    <MetricCard label="Risk Score" value={`${activeAnalysis.risk_score}/100`} tone={activeAnalysis.risk_score >= 50 ? "critical" : activeAnalysis.risk_score >= 25 ? "warning" : "neutral"} />
                  </div>

                  {/* Benford's Law chart */}
                  <section className="content-card" style={{ marginTop: 20 }}>
                    <div className="mini-header">
                      <span>Benford&apos;s Law Analysis</span>
                      <span className={activeAnalysis.benford_is_suspicious ? "risk-chip critical" : "risk-chip low"}>
                        {activeAnalysis.benford_is_suspicious ? "⚠️ Suspicious" : "✓ Normal"}
                      </span>
                    </div>
                    <p className="muted-copy" style={{ margin: "8px 0" }}>
                      Leading digit distribution compared to Benford&apos;s expected frequencies. χ²={activeAnalysis.benford_chi_squared.toFixed(2)}, p={activeAnalysis.benford_p_value.toFixed(4)}
                    </p>
                    <div className="benford-chart">
                      {activeAnalysis.benford_digits.map((d) => (
                        <div key={d.digit} className="benford-bar-group">
                          <div className="benford-bars">
                            <div className="benford-bar expected" style={{ height: `${Math.max(d.expected_pct * 3, 2)}px` }} title={`Expected: ${d.expected_pct}%`} />
                            <div
                              className={`benford-bar actual ${Math.abs(d.deviation) > 5 ? "deviant" : ""}`}
                              style={{ height: `${Math.max(d.actual_pct * 3, 2)}px` }}
                              title={`Actual: ${d.actual_pct}%`}
                            />
                          </div>
                          <span className="benford-label">{d.digit}</span>
                        </div>
                      ))}
                    </div>
                    <div className="benford-legend">
                      <span><span className="legend-swatch expected" /> Expected</span>
                      <span><span className="legend-swatch actual" /> Actual</span>
                    </div>
                  </section>

                  {/* Velocity spikes */}
                  {activeAnalysis.velocity_spikes.length > 0 && (
                    <section className="content-card" style={{ marginTop: 16 }}>
                      <div className="mini-header"><span>Velocity Spikes</span><span>{activeAnalysis.velocity_spikes.length}</span></div>
                      <div className="stack">
                        {activeAnalysis.velocity_spikes.map((spike, i) => (
                          <article key={`spike-${i}`} className="alert-card">
                            <div className="alert-card-header">
                              <span className="risk-chip high">z={spike.z_score}</span>
                              <strong>{spike.entity_id}</strong>
                            </div>
                            <p className="muted-copy">
                              {spike.transaction_count} transactions totaling {currencyFormatter.format(spike.total_amount)} in one window
                              (baseline: {spike.baseline_avg_count} txns/window)
                            </p>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* All anomalies */}
                  {activeAnalysis.anomalies.length > 0 && (
                    <section className="content-card" style={{ marginTop: 16 }}>
                      <div className="mini-header"><span>All Anomaly Flags</span><span>{activeAnalysis.anomalies.length}</span></div>
                      <div className="stack">
                        {activeAnalysis.anomalies.slice(0, 30).map((anomaly) => (
                          <article key={anomaly.anomaly_id} className="alert-card">
                            <div className="alert-card-header">
                              <div>
                                <span className={`risk-chip ${anomaly.severity}`}>{anomaly.severity}</span>
                                <span className="status-chip open">{anomaly.anomaly_type}</span>
                              </div>
                              <span className="weight-pill">{(anomaly.score * 100).toFixed(0)}%</span>
                            </div>
                            <h4>{anomaly.title}</h4>
                            <p className="muted-copy">{anomaly.description}</p>
                          </article>
                        ))}
                        {activeAnalysis.anomalies.length > 30 && (
                          <p className="muted-copy">...and {activeAnalysis.anomalies.length - 30} more anomalies</p>
                        )}
                      </div>
                    </section>
                  )}
                </div>
              )}
            </section>
          )}

          {/* ======= CASES ======= */}
          {activeView === "cases" && (
            <section className="surface" style={{ padding: 24 }}>
              <div className="section-header"><span>Fraud Cases</span><span>{cases.length} total</span></div>
              {cases.length === 0 ? (
                <div className="empty-state">No cases yet. Investigate a scenario and create one.</div>
              ) : (
                <div className="stack">
                  {cases.map((c) => (
                    <article key={c.case_id} className="case-card">
                      <div className="case-card-header">
                        <div>
                          <span className={`risk-chip ${c.risk_level}`}>{c.priority}</span>
                          <span className={`status-chip ${c.status}`}>{c.status}</span>
                        </div>
                        <span className="case-date">{dateFormatter.format(new Date(c.created_at))}</span>
                      </div>
                      <h3>{c.title}</h3>
                      <p className="muted-copy">{c.summary}</p>
                      <div className="case-card-footer">
                        <span>Risk: {c.risk_score}/100</span>
                        <span>{c.comment_count} comments</span>
                        {c.sla_deadline && <span>SLA: {dateFormatter.format(new Date(c.sla_deadline))}</span>}
                        {c.status !== "resolved" && c.status !== "closed" && (
                          <button className="small-button" onClick={() => handleResolveCase(c.case_id)} type="button">Resolve</button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* ======= ALERTS ======= */}
          {activeView === "alerts" && (
            <section className="surface" style={{ padding: 24 }}>
              <div className="section-header"><span>Fraud Alerts</span><span>{alerts.length} total</span></div>
              {alerts.length === 0 ? (
                <div className="empty-state">No alerts yet. They are auto-generated when investigations detect risk.</div>
              ) : (
                <div className="stack">
                  {alerts.map((alert) => (
                    <article key={alert.alert_id} className="alert-card">
                      <div className="alert-card-header">
                        <span className={`risk-chip ${alert.severity}`}>{alert.severity}</span>
                        <span className={`status-chip ${alert.status}`}>{alert.status}</span>
                        <span className="tag-pill">{alert.rule_code}</span>
                      </div>
                      <h3>{alert.title}</h3>
                      <p className="muted-copy">{alert.narrative}</p>
                      <div className="case-card-footer">
                        <span>{dateFormatter.format(new Date(alert.created_at))}</span>
                        {alert.status === "new" && (
                          <button className="small-button" onClick={() => handleAcknowledgeAlert(alert.alert_id)} type="button">Acknowledge</button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* ======= AUDIT ======= */}
          {activeView === "audit" && operator.role === "admin" && (
            <section className="surface" style={{ padding: 24 }}>
              <div className="section-header"><span>Audit Trail</span><span>{auditEvents.length}</span></div>
              <div className="stack">
                {auditEvents.map((event) => (
                  <article key={event.event_id} className="transaction-row">
                    <div>
                      <strong>{event.action}</strong>
                      <p>{event.actor_username ?? "anonymous"} on {event.path}</p>
                    </div>
                    <div className="transaction-meta">
                      <strong>{event.status_code}</strong>
                      <span>{dateFormatter.format(new Date(event.occurred_at))}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
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
