"use client";

import { FormEvent, useDeferredValue, useEffect, useState, useTransition } from "react";

import {
  AlertsSection,
  AnalysisCopilotCard,
  AuditSection,
  CasesSection,
  DashboardHeader,
  DashboardNav,
  MetricCard,
  OverviewSection,
  SignedOutPanel,
  type ActiveView,
} from "@/components/dashboard-sections";
import {
  analyzeDataset,
  createCase,
  fetchAlerts,
  fetchAnalysisExplanation,
  fetchAnalysisResult,
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
  AnalysisExplanation,
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
  WorkspaceGuide,
} from "@/lib/contracts";

type DashboardProps = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
  workspaceGuide: WorkspaceGuide | null;
};

type RefreshOptions = {
  alerts?: boolean;
  audit?: boolean;
  cases?: boolean;
  datasets?: boolean;
  stats?: boolean;
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

export function Dashboard({
  backendHealth,
  bootstrapError,
  workspaceGuide,
}: DashboardProps) {
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
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisResultData | null>(null);
  const [analysisExplanation, setAnalysisExplanation] = useState<AnalysisExplanation | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingAnalysisDetail, setIsLoadingAnalysisDetail] = useState(false);
  const [activeView, setActiveView] = useState<ActiveView>("overview");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(bootstrapError);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [analysisDetailError, setAnalysisDetailError] = useState<string | null>(null);
  const [analysisExplanationError, setAnalysisExplanationError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isPending, startTransition] = useTransition();

  const deferredQuery = useDeferredValue(searchQuery);
  const deferredSignals = useDeferredValue(investigation?.investigation.text_signals ?? []);
  const showBootstrapCredentials =
    backendHealth?.environment === "local" || backendHealth?.environment === "test";
  const selectedScenario =
    scenarios.find((scenario) => scenario.scenario_id === selectedScenarioId) ??
    scenarios[0] ??
    null;
  const activeInvestigation = investigation?.investigation ?? null;
  const activeInvestigationMatchesSelection =
    activeInvestigation?.scenario.scenario_id === selectedScenarioId;
  const selectedDataset =
    datasets.find((dataset) => dataset.dataset_id === selectedDatasetId) ?? null;
  const activeAnalysisMatchesSelection = activeAnalysis?.dataset_id === selectedDatasetId;
  const visibleScenarios = scenarios.filter((scenario) => {
    const query = deferredQuery.trim().toLowerCase();
    if (!query) return true;
    return [scenario.title, scenario.industry, scenario.summary, scenario.hypothesis, ...scenario.tags]
      .join(" ")
      .toLowerCase()
      .includes(query);
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
      clearSessionState("Your session could not be restored.");
      window.localStorage.removeItem(tokenStorageKey);
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
      // The signed-in workspace still works without these secondary slices.
    }

    const preferredDataset =
      nextDatasets.find((dataset) => dataset.status === "completed") ?? nextDatasets[0] ?? null;

    setOperator(principal);
    setScenarios(scenarioCatalog.scenarios);
    setSelectedScenarioId(firstScenarioId);
    setInvestigation(null);
    setAuditEvents(nextAuditEvents);
    setDashboardStats(nextStats);
    setCases(nextCases);
    setAlerts(nextAlerts);
    setDatasets(nextDatasets);
    setSelectedDatasetId(preferredDataset?.dataset_id ?? null);
    setActiveAnalysis(null);
    setAnalysisExplanation(null);
    setAnalysisDetailError(null);
    setAnalysisExplanationError(null);
    setActiveView(defaultViewForRole(principal.role));

    if (preferredDataset?.status === "completed") {
      await loadDatasetDetail(
        token,
        preferredDataset.dataset_id,
        principal.role,
      );
    }
  }

  async function refreshWorkspaceSlices(
    token: string,
    {
      alerts = false,
      audit = false,
      cases = false,
      datasets = false,
      stats = false,
    }: RefreshOptions,
  ): Promise<void> {
    const shouldRefreshAudit = audit && operator?.role === "admin";
    const [alertsResult, auditResult, casesResult, datasetsResult, statsResult] =
      await Promise.allSettled([
        alerts ? fetchAlerts(token) : Promise.resolve(null),
        shouldRefreshAudit ? fetchAuditEvents(token) : Promise.resolve(null),
        cases ? fetchCases(token) : Promise.resolve(null),
        datasets ? fetchDatasets(token) : Promise.resolve(null),
        stats ? fetchDashboardStats(token) : Promise.resolve(null),
      ] as const);

    if (alertsResult.status === "fulfilled" && alertsResult.value) {
      setAlerts(alertsResult.value.alerts);
    }
    if (auditResult.status === "fulfilled" && auditResult.value) {
      setAuditEvents(auditResult.value.events);
    }
    if (casesResult.status === "fulfilled" && casesResult.value) {
      setCases(casesResult.value.cases);
    }
    if (datasetsResult.status === "fulfilled" && datasetsResult.value) {
      setDatasets(datasetsResult.value.datasets);
    }
    if (statsResult.status === "fulfilled" && statsResult.value) {
      setDashboardStats(statsResult.value.stats);
    }
  }

  async function handleScenarioSelection(scenarioId: string) {
    if (!authToken) return;
    setSelectedScenarioId(scenarioId);
    setActiveView("investigate");
    setErrorMessage(null);
    setInvestigation(null);
    startTransition(() => {
      void loadInvestigation(authToken, scenarioId);
    });
  }

  async function loadInvestigation(token: string, scenarioId: string) {
    try {
      const nextInvestigation = await fetchInvestigationClient(token, scenarioId);
      setInvestigation(nextInvestigation);
      await refreshWorkspaceSlices(token, { alerts: true, audit: true, stats: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load investigation.");
    }
  }

  async function loadDatasetDetail(
    token: string,
    datasetId: string,
    role: OperatorPrincipal["role"],
    knownAnalysis?: AnalysisResultData,
  ) {
    setSelectedDatasetId(datasetId);
    setIsLoadingAnalysisDetail(true);
    setAnalysisDetailError(null);
    setAnalysisExplanationError(null);
    setErrorMessage(null);
    if (!knownAnalysis) {
      setActiveAnalysis(null);
    }
    setAnalysisExplanation(null);

    const analysisPromise = knownAnalysis
      ? Promise.resolve({ analysis: knownAnalysis })
      : fetchAnalysisResult(token, datasetId);
    const explanationPromise = fetchAnalysisExplanation(
      token,
      datasetId,
      role === "admin" ? "admin" : "analyst",
    );

    const [analysisResult, explanationResult] = await Promise.allSettled([
      analysisPromise,
      explanationPromise,
    ]);

    if (analysisResult.status === "fulfilled") {
      setActiveAnalysis(analysisResult.value.analysis);
    } else {
      const message =
        analysisResult.reason instanceof Error
          ? analysisResult.reason.message
          : "Could not load analysis details.";
      setAnalysisDetailError(message);
    }

    if (explanationResult.status === "fulfilled") {
      setAnalysisExplanation(explanationResult.value.explanation);
    } else {
      const message =
        explanationResult.reason instanceof Error
          ? explanationResult.reason.message
          : "Could not load the copilot brief.";
      setAnalysisExplanationError(message);
    }

    setIsLoadingAnalysisDetail(false);
  }

  async function handleCreateCase() {
    if (!authToken || !activeInvestigation) return;
    try {
      await createCase(authToken, {
        source_type: "scenario",
        source_id: activeInvestigation.scenario.scenario_id,
        scenario_id: activeInvestigation.scenario.scenario_id,
        title: activeInvestigation.scenario.title,
        summary: activeInvestigation.summary,
        priority: activeInvestigation.risk_level,
        risk_score: activeInvestigation.total_risk_score,
        risk_level: activeInvestigation.risk_level,
      });
      await refreshWorkspaceSlices(authToken, { audit: true, cases: true, stats: true });
      setActiveView("cases");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create case.");
    }
  }

  async function handleAcknowledgeAlert(alertId: string) {
    if (!authToken) return;
    try {
      await updateAlertStatus(authToken, alertId, { status: "acknowledged" });
      await refreshWorkspaceSlices(authToken, { alerts: true, audit: true, stats: true });
    } catch {
      // Inline analyst action, no modal path needed.
    }
  }

  async function handleResolveCase(caseId: string) {
    if (!authToken) return;
    try {
      await updateCaseStatus(authToken, caseId, {
        status: "resolved",
        disposition: "confirmed-fraud",
      });
      await refreshWorkspaceSlices(authToken, { audit: true, cases: true, stats: true });
    } catch {
      // Inline analyst action, no modal path needed.
    }
  }

  async function handleUploadDataset(file: File) {
    if (!authToken) return;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      const uploadedDataset = await uploadDataset(authToken, file);
      setSelectedDatasetId(uploadedDataset.dataset_id);
      setActiveAnalysis(null);
      setAnalysisExplanation(null);
      setAnalysisDetailError(null);
      setAnalysisExplanationError(null);
      setActiveView("analyze");
      await refreshWorkspaceSlices(authToken, { audit: true, datasets: true, stats: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDatasetSelection(dataset: DatasetInfo) {
    if (!authToken || !operator) return;
    setActiveView("analyze");
    setSelectedDatasetId(dataset.dataset_id);
    setErrorMessage(null);

    if (dataset.status === "completed") {
      await loadDatasetDetail(authToken, dataset.dataset_id, operator.role);
      return;
    }

    setActiveAnalysis(null);
    setAnalysisExplanation(null);
    setAnalysisDetailError(null);
    setAnalysisExplanationError(null);
  }

  async function handleAnalyzeDataset(datasetId: string) {
    if (!authToken || !operator) return;
    setIsAnalyzing(true);
    setActiveView("analyze");
    setSelectedDatasetId(datasetId);
    setErrorMessage(null);
    try {
      const result = await analyzeDataset(authToken, datasetId);
      await loadDatasetDetail(authToken, datasetId, operator.role, result.analysis);
      await refreshWorkspaceSlices(authToken, {
        alerts: true,
        audit: true,
        datasets: true,
        stats: true,
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Analysis failed.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleCreateCaseFromAnalysis() {
    if (!authToken || !activeAnalysis) return;
    const dataset = datasets.find((item) => item.dataset_id === activeAnalysis.dataset_id);
    try {
      await createCase(authToken, {
        source_type: "dataset",
        source_id: activeAnalysis.dataset_id,
        title: dataset ? `Dataset review: ${dataset.name}` : "Dataset review",
        summary: activeAnalysis.summary,
        priority: activeAnalysis.risk_level,
        risk_score: activeAnalysis.risk_score,
        risk_level: activeAnalysis.risk_level,
      });
      await refreshWorkspaceSlices(authToken, { audit: true, cases: true, stats: true });
      setActiveView("cases");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create case.");
    }
  }

  function handleLogout() {
    window.localStorage.removeItem(tokenStorageKey);
    clearSessionState(null);
  }

  function clearSessionState(nextLoginError: string | null) {
    setAuthToken(null);
    setOperator(null);
    setScenarios([]);
    setSelectedScenarioId(null);
    setInvestigation(null);
    setAuditEvents([]);
    setCases([]);
    setAlerts([]);
    setDashboardStats(null);
    setDatasets([]);
    setSelectedDatasetId(null);
    setActiveAnalysis(null);
    setAnalysisExplanation(null);
    setLoginError(nextLoginError);
    setAnalysisDetailError(null);
    setAnalysisExplanationError(null);
    setErrorMessage(null);
    setUsername("");
    setPassword("");
    setActiveView("overview");
  }

  return (
    <main className="page-shell">
      <DashboardHeader
        backendHealth={backendHealth}
        operator={operator}
        workspaceGuide={workspaceGuide}
      />

      {!operator || !authToken ? (
        <SignedOutPanel
          backendHealth={backendHealth}
          isAuthenticating={isAuthenticating}
          loginError={loginError}
          password={password}
          showBootstrapCredentials={showBootstrapCredentials}
          username={username}
          workspaceGuide={workspaceGuide}
          onPasswordChange={setPassword}
          onSubmit={handleLogin}
          onUsernameChange={setUsername}
        />
      ) : (
        <>
          <DashboardNav
            activeView={activeView}
            alerts={alerts}
            cases={cases}
            operator={operator}
            onLogout={handleLogout}
            onViewChange={setActiveView}
          />

          {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}

          {activeView === "overview" && (
            <OverviewSection
              dashboardStats={dashboardStats}
              datasetsCount={datasets.length}
              scenariosCount={scenarios.length}
              workspaceGuide={workspaceGuide}
              onViewChange={setActiveView}
            />
          )}

          {activeView === "investigate" && (
            <section className="dashboard-view-stack">
              <section className="content-card overview-hero">
                <div>
                  <p className="eyebrow">Reference scenarios</p>
                  <h2>Use seeded investigations to validate the rule engine and train operators.</h2>
                </div>
                <div className="llm-note compact">
                  <strong>Secondary workflow</strong>
                  <p>
                    These scenarios are for validation, regression checks, and analyst practice.
                    The primary product path still starts from uploaded datasets.
                  </p>
                </div>
              </section>

              <section className="workspace-grid">
                <aside className="surface scenario-rail">
                  <div className="rail-toolbar">
                    <div className="section-header">
                      <span>Reference Scenarios</span>
                      <span>{visibleScenarios.length}</span>
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
                      <div className="empty-state">No scenarios match that search.</div>
                    )}
                  </div>
                </aside>

                <section className="surface investigation-panel">
                  {selectedScenario && activeInvestigation && activeInvestigationMatchesSelection ? (
                    <>
                      <div className="section-header">
                        <span>Active Investigation</span>
                        <span>{isPending ? "Refreshing evidence..." : "Reference analyst view"}</span>
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
                              style={{ width: `${riskMeterWidth[activeInvestigation.risk_level]}%` }}
                            />
                          </div>
                          <span className={`risk-chip ${activeInvestigation.risk_level}`}>
                            {activeInvestigation.risk_level}
                          </span>
                        </div>
                      </div>

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

                      {activeInvestigation.graph_analysis ? (
                        <section className="content-card emphasis-card">
                          <div className="mini-header">
                            <span>Graph Analysis</span>
                            <span>Relationship network</span>
                          </div>
                          <div className="metrics-grid" style={{ marginTop: 12 }}>
                            <MetricCard
                              label="Components"
                              tone="neutral"
                              value={String(activeInvestigation.graph_analysis.connected_components)}
                            />
                            <MetricCard
                              label="Density"
                              tone={
                                activeInvestigation.graph_analysis.density > 0.3
                                  ? "warning"
                                  : "neutral"
                              }
                              value={activeInvestigation.graph_analysis.density.toFixed(3)}
                            />
                            <MetricCard
                              label="Communities"
                              tone="neutral"
                              value={String(activeInvestigation.graph_analysis.community_count)}
                            />
                            <MetricCard
                              label="Risk amplifier"
                              tone={
                                activeInvestigation.graph_analysis.risk_amplification_factor > 1.3
                                  ? "critical"
                                  : "good"
                              }
                              value={`${activeInvestigation.graph_analysis.risk_amplification_factor}x`}
                            />
                          </div>
                          {activeInvestigation.graph_analysis.hub_entities.length > 0 ? (
                            <div style={{ marginTop: 12 }}>
                              <p className="eyebrow" style={{ marginBottom: 8 }}>
                                Hub entities
                              </p>
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
                        <button className="primary-button" onClick={handleCreateCase} type="button">
                          Create case from investigation
                        </button>
                      </div>

                      <div className="insight-grid">
                        <section className="content-card emphasis-card">
                          <div className="mini-header">
                            <span>Recommended Actions</span>
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
                            <span>Reasoning</span>
                            <strong>{activeInvestigation.provider_summary.active_reasoning_provider}</strong>
                            <span>Text</span>
                            <strong>{activeInvestigation.provider_summary.active_text_provider}</strong>
                            <span>Database</span>
                            <strong>{backendHealth?.database_status ?? "unavailable"}</strong>
                            <span>Rate limit</span>
                            <strong>{backendHealth?.rate_limit_backend ?? "unavailable"}</strong>
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
                            <span>Suspicious Transactions</span>
                            <span>{activeInvestigation.suspicious_transactions.length}</span>
                          </div>
                          <div className="stack">
                            {activeInvestigation.suspicious_transactions.map((txn) => (
                              <article key={txn.transaction_id} className="transaction-row">
                                <div>
                                  <strong>{txn.transaction_id}</strong>
                                  <p>
                                    {txn.merchant_id} via {txn.channel}
                                  </p>
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
                        onClick={() => handleScenarioSelection(selectedScenario.scenario_id)}
                        type="button"
                      >
                        {isPending
                          ? "Running reference investigation..."
                          : "Run reference investigation"}
                      </button>
                    </div>
                  ) : (
                    <div className="empty-state">
                      Select a reference scenario to validate the investigation engine.
                    </div>
                  )}
                </section>
              </section>
            </section>
          )}

          {activeView === "analyze" && (
            <section className="dashboard-view-stack">
              <section className="content-card overview-hero">
                <div>
                  <p className="eyebrow">
                    {workspaceGuide?.primary_workflow_title ?? "Primary Workflow"}
                  </p>
                  <h2>Move uploaded transaction data through one deterministic workflow.</h2>
                  <p className="muted-copy">
                    Upload data, run statistical analysis, review the generated alerts, and
                    create a case only when the evidence warrants it.
                  </p>
                </div>
                <div className="llm-note compact">
                  <strong>Copilot boundary</strong>
                  <p>
                    {workspaceGuide?.llm_positioning_note ??
                      "The explanation layer rewrites deterministic findings. It does not change scores or thresholds."}
                  </p>
                </div>
              </section>

              {dashboardStats?.workflow_stages && dashboardStats.workflow_stages.length > 0 ? (
                <section className="workflow-strip compact">
                  {dashboardStats.workflow_stages.map((stage) => (
                    <article key={stage.stage_id} className="workflow-stage-card">
                      <div className="mini-header">
                        <span>{stage.title}</span>
                        <span>{stage.total_count}</span>
                      </div>
                      <p className="muted-copy">{stage.description}</p>
                      <div className="workflow-stage-foot">
                        <strong>{stage.highlighted_count}</strong>
                        <span>{stage.highlighted_label}</span>
                      </div>
                    </article>
                  ))}
                </section>
              ) : null}

              <section className="analysis-workspace-grid">
                <aside className="surface dataset-rail">
                  <div className="section-header">
                    <span>Dataset Queue</span>
                    <span>{datasets.length}</span>
                  </div>

                  <div className="upload-zone">
                    <p>
                      <strong>Upload a transaction CSV</strong>
                    </p>
                    <p className="muted-copy">
                      Required columns: <code>transaction_id</code>, <code>account_id</code>,{" "}
                      <code>amount</code>, <code>timestamp</code>
                    </p>
                    <input
                      accept=".csv"
                      disabled={isUploading}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void handleUploadDataset(file);
                        event.target.value = "";
                      }}
                      type="file"
                    />
                    {isUploading ? <p className="muted-copy">Uploading...</p> : null}
                    <p className="muted-copy" style={{ marginTop: 8 }}>
                      Sample dataset: <code>docs/sample_data/sample_transactions.csv</code>
                    </p>
                  </div>

                  {datasets.length === 0 ? (
                    <div className="empty-state">
                      No datasets yet. Upload one to start the primary workflow.
                    </div>
                  ) : (
                    <div className="dataset-list">
                      {datasets.map((dataset) => {
                        const isSelected = dataset.dataset_id === selectedDatasetId;
                        return (
                          <article
                            key={dataset.dataset_id}
                            className={`dataset-card ${isSelected ? "selected" : ""}`}
                          >
                            <button
                              className="dataset-select"
                              onClick={() => void handleDatasetSelection(dataset)}
                              type="button"
                            >
                              <div className="case-card-header">
                                <div>
                                  <span
                                    className={`status-chip ${
                                      dataset.status === "completed"
                                        ? "resolved"
                                        : dataset.status === "failed"
                                          ? "escalated"
                                          : "open"
                                    }`}
                                  >
                                    {dataset.status}
                                  </span>
                                  <strong>{dataset.name}</strong>
                                </div>
                                <span className="case-date">
                                  {dateFormatter.format(new Date(dataset.uploaded_at))}
                                </span>
                              </div>
                              <p className="muted-copy">
                                {dataset.row_count.toLocaleString()} transactions
                              </p>
                              {dataset.error_message ? (
                                <div className="error-banner">{dataset.error_message}</div>
                              ) : null}
                            </button>
                            <div className="dataset-card-actions">
                              {dataset.status === "uploaded" ? (
                                <button
                                  className="primary-button"
                                  disabled={isAnalyzing}
                                  onClick={() => void handleAnalyzeDataset(dataset.dataset_id)}
                                  type="button"
                                >
                                  {isAnalyzing && selectedDatasetId === dataset.dataset_id
                                    ? "Analyzing..."
                                    : "Run analysis"}
                                </button>
                              ) : null}
                              {dataset.status === "completed" ? (
                                <>
                                  <button
                                    className="secondary-button"
                                    onClick={() => void handleDatasetSelection(dataset)}
                                    type="button"
                                  >
                                    View analysis
                                  </button>
                                  <button
                                    className="small-button"
                                    disabled={isAnalyzing}
                                    onClick={() => void handleAnalyzeDataset(dataset.dataset_id)}
                                    type="button"
                                  >
                                    Re-analyze
                                  </button>
                                </>
                              ) : null}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </aside>

                <section className="surface analysis-detail-panel">
                  {selectedDataset?.status === "uploaded" ? (
                    <div className="empty-state">
                      <p style={{ marginBottom: 12 }}>
                        <strong>{selectedDataset.name}</strong>
                      </p>
                      <p className="muted-copy" style={{ marginBottom: 16 }}>
                        This dataset is waiting for deterministic analysis.
                      </p>
                      <button
                        className="primary-button"
                        disabled={isAnalyzing}
                        onClick={() => void handleAnalyzeDataset(selectedDataset.dataset_id)}
                        type="button"
                      >
                        {isAnalyzing ? "Analyzing..." : "Run dataset analysis"}
                      </button>
                    </div>
                  ) : null}

                  {selectedDataset?.status === "failed" ? (
                    <div className="empty-state">
                      <p style={{ marginBottom: 12 }}>
                        <strong>{selectedDataset.name}</strong>
                      </p>
                      <p className="muted-copy">
                        This dataset failed processing. Review the dataset error and upload a corrected
                        file.
                      </p>
                    </div>
                  ) : null}

                  {selectedDataset?.status === "analyzing" ? (
                    <div className="empty-state">
                      Deterministic analysis is currently running for this dataset.
                    </div>
                  ) : null}

                  {selectedDataset?.status === "completed" &&
                  isLoadingAnalysisDetail &&
                  !activeAnalysisMatchesSelection ? (
                    <div className="empty-state">
                      Loading the completed analysis and copilot brief for this dataset.
                    </div>
                  ) : null}

                  {selectedDataset?.status === "completed" &&
                  analysisDetailError &&
                  !activeAnalysisMatchesSelection ? (
                    <div className="error-banner">{analysisDetailError}</div>
                  ) : null}

                  {!selectedDataset ? (
                    <div className="empty-state">
                      Select a dataset from the queue to inspect its workflow status.
                    </div>
                  ) : null}

                  {selectedDataset &&
                  selectedDataset.status === "completed" &&
                  activeAnalysis &&
                  activeAnalysisMatchesSelection ? (
                    <div className="stack">
                      <div className="section-header">
                        <span>Analysis Review</span>
                        <span className={`risk-chip ${activeAnalysis.risk_level}`}>
                          {activeAnalysis.risk_score}/100 {activeAnalysis.risk_level}
                        </span>
                      </div>

                      <section className="content-card emphasis-card">
                        <div className="headline-row">
                          <div className="headline-copy">
                            <p className="eyebrow">Selected dataset</p>
                            <h2>{selectedDataset.name}</h2>
                            <p className="summary-lead">{activeAnalysis.summary}</p>
                          </div>
                          <div className="risk-meter-shell">
                            <div className="risk-meter-label">
                              <span>Deterministic score</span>
                              <strong>{activeAnalysis.risk_score}/100</strong>
                            </div>
                            <div className="risk-meter-track">
                              <div
                                className={`risk-meter-fill ${activeAnalysis.risk_level}`}
                                style={{ width: `${riskMeterWidth[activeAnalysis.risk_level]}%` }}
                              />
                            </div>
                            <span className={`risk-chip ${activeAnalysis.risk_level}`}>
                              {activeAnalysis.risk_level}
                            </span>
                          </div>
                        </div>

                        <div className="metrics-grid">
                          <MetricCard
                            label="Transactions"
                            tone="neutral"
                            value={activeAnalysis.total_transactions.toLocaleString()}
                          />
                          <MetricCard
                            label="Anomalies"
                            tone={activeAnalysis.total_anomalies > 0 ? "critical" : "neutral"}
                            value={String(activeAnalysis.total_anomalies)}
                          />
                          <MetricCard
                            label="Outliers"
                            tone={activeAnalysis.outlier_count > 0 ? "warning" : "neutral"}
                            value={`${activeAnalysis.outlier_count} (${activeAnalysis.outlier_pct}%)`}
                          />
                          <MetricCard
                            label="Velocity spikes"
                            tone={activeAnalysis.velocity_spikes.length > 0 ? "warning" : "neutral"}
                            value={String(activeAnalysis.velocity_spikes.length)}
                          />
                        </div>

                        <div className="action-bar">
                          <button
                            className="primary-button"
                            onClick={handleCreateCaseFromAnalysis}
                            type="button"
                          >
                            Create case from dataset analysis
                          </button>
                        </div>
                      </section>

                      {analysisDetailError ? <div className="error-banner">{analysisDetailError}</div> : null}

                      <div className="analysis-summary-grid">
                        <section className="stack">
                          <section className="content-card">
                            <div className="mini-header">
                              <span>Benford&apos;s Law</span>
                              <span>
                                p={activeAnalysis.benford_p_value.toFixed(4)}
                              </span>
                            </div>
                            <p className="muted-copy" style={{ margin: "8px 0" }}>
                              Leading-digit distribution compared against Benford&apos;s expected
                              frequencies. Suspicion is deterministic and threshold-based.
                            </p>
                            <div className="benford-chart">
                              {activeAnalysis.benford_digits.map((digit) => (
                                <div key={digit.digit} className="benford-bar-group">
                                  <div className="benford-bars">
                                    <div
                                      className="benford-bar expected"
                                      style={{ height: `${Math.max(digit.expected_pct * 3, 2)}px` }}
                                      title={`Expected: ${digit.expected_pct}%`}
                                    />
                                    <div
                                      className={`benford-bar ${digit.deviation > 0 ? "critical" : "neutral"}`}
                                      style={{ height: `${Math.max(digit.actual_pct * 3, 2)}px` }}
                                      title={`Actual: ${digit.actual_pct}%`}
                                    />
                                  </div>
                                  <span>{digit.digit}</span>
                                </div>
                              ))}
                            </div>
                          </section>

                          <section className="content-card">
                            <div className="mini-header">
                              <span>Anomaly Findings</span>
                              <span>{activeAnalysis.anomalies.length}</span>
                            </div>
                            <div className="stack">
                              {activeAnalysis.anomalies.map((anomaly) => (
                                <article key={anomaly.anomaly_id} className="signal-card">
                                  <div className="signal-card-top">
                                    <strong>{anomaly.title}</strong>
                                    <span className={`risk-chip ${anomaly.severity}`}>
                                      {anomaly.severity}
                                    </span>
                                  </div>
                                  <p>{anomaly.description}</p>
                                  <span className="signal-meta">
                                    {anomaly.anomaly_type} on {anomaly.affected_entity_type}{" "}
                                    {anomaly.affected_entity_id}
                                  </span>
                                </article>
                              ))}
                            </div>
                          </section>

                          {activeAnalysis.velocity_spikes.length > 0 ? (
                            <section className="content-card">
                              <div className="mini-header">
                                <span>Velocity Windows</span>
                                <span>{activeAnalysis.velocity_spikes.length}</span>
                              </div>
                              <div className="stack">
                                {activeAnalysis.velocity_spikes.map((spike) => (
                                  <article
                                    key={`${spike.entity_type}-${spike.entity_id}-${spike.window_start}`}
                                    className="transaction-row"
                                  >
                                    <div>
                                      <strong>
                                        {spike.entity_type} {spike.entity_id}
                                      </strong>
                                      <p>
                                        {spike.transaction_count} transactions for{" "}
                                        {currencyFormatter.format(spike.total_amount)}
                                      </p>
                                    </div>
                                    <div className="transaction-meta">
                                      <strong>{spike.z_score.toFixed(1)}σ</strong>
                                      <span>
                                        {dateFormatter.format(new Date(spike.window_start))}
                                      </span>
                                    </div>
                                  </article>
                                ))}
                              </div>
                            </section>
                          ) : null}
                        </section>

                        <AnalysisCopilotCard
                          explanation={analysisExplanation}
                          isLoading={isLoadingAnalysisDetail}
                          loadError={analysisExplanationError}
                        />
                      </div>
                    </div>
                  ) : null}
                </section>
              </section>
            </section>
          )}

          {activeView === "cases" && (
            <CasesSection
              cases={cases}
              dateFormatter={dateFormatter}
              onResolveCase={handleResolveCase}
            />
          )}

          {activeView === "alerts" && (
            <AlertsSection
              alerts={alerts}
              dateFormatter={dateFormatter}
              onAcknowledgeAlert={handleAcknowledgeAlert}
            />
          )}

          {activeView === "audit" && operator.role === "admin" ? (
            <AuditSection auditEvents={auditEvents} dateFormatter={dateFormatter} />
          ) : null}
        </>
      )}
    </main>
  );
}

function defaultViewForRole(role: OperatorPrincipal["role"]): ActiveView {
  return role === "admin" ? "overview" : "analyze";
}
