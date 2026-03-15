"use client";

import { useState } from "react";

import {
  BenfordChart,
  RiskGauge,
  VelocityChart,
} from "@/components/charts";
import {
  AlertsSection,
  AnalysisSummaryCard,
  AuditSection,
  CasesSection,
  DashboardHeader,
  MetricCard,
  OverviewSection,
  SignedOutPanel,
} from "@/components/dashboard-sections";
import { MobileMenuButton, Sidebar, TopBar, type ActiveView } from "@/components/sidebar";
import { SkeletonCard, SkeletonMetricRow, SkeletonList } from "@/components/skeletons";
import { useDashboardState } from "@/lib/use-dashboard-state";
import type {
  HealthResponse,
  WorkspaceGuide,
} from "@/lib/contracts";

type DashboardProps = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
  workspaceGuide: WorkspaceGuide | null;
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
  const [state, actions] = useDashboardState(backendHealth, bootstrapError);
  const {
    authToken,
    operator,
    username,
    password,
    isAuthenticating,
    loginError,
    showBootstrapCredentials,
    activeView,
    isPending,
    errorMessage,
    scenarios,
    selectedScenarioId,
    selectedScenario,
    activeInvestigation,
    activeInvestigationMatchesSelection,
    visibleScenarios,
    searchQuery,
    deferredSignals,
    cases,
    selectedCaseId,
    activeCaseDetail,
    isLoadingCaseDetail,
    caseDetailError,
    isSubmittingCaseComment,
    alerts,
    auditEvents,
    dashboardStats,
    datasets,
    selectedDatasetId,
    selectedDataset,
    activeAnalysis,
    activeAnalysisMatchesSelection,
    analysisExplanation,
    isUploading,
    isAnalyzing,
    isLoadingAnalysisDetail,
    analysisDetailError,
    analysisExplanationError,
  } = state;
  const {
    setUsername,
    setPassword,
    setActiveView,
    setSearchQuery,
    handleLogin,
    handleLogout,
    handleScenarioSelection,
    handleCreateCase,
    handleAcknowledgeAlert,
    handleCaseSelection,
    handleAddCaseComment,
    handleResolveCase,
    handleCreateCaseFromAlert,
    handleUploadDataset,
    handleDatasetSelection,
    handleAnalyzeDataset,
    handleCreateCaseFromAnalysis,
  } = actions;

  const viewTitles: Record<ActiveView, string> = {
    overview: "Overview",
    analyze: "Analyze Data",
    alerts: "Fraud Alerts",
    cases: "Fraud Cases",
    investigate: "Scenarios",
    audit: "Audit Trail",
  };

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!operator || !authToken) {
    return (
      <main id="main-content" className="page-shell" style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 40px" }}>
        <DashboardHeader
          backendHealth={backendHealth}
          operator={operator}
          workspaceGuide={workspaceGuide}
        />
        <SignedOutPanel
          backendHealth={backendHealth}
          bootstrapError={bootstrapError}
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
      </main>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar
        activeView={activeView}
        alerts={alerts}
        cases={cases}
        mobileOpen={mobileMenuOpen}
        operator={operator}
        onLogout={handleLogout}
        onMobileClose={() => setMobileMenuOpen(false)}
        onViewChange={setActiveView}
      />

      <main id="main-content" className="app-main" tabIndex={-1}>
        <TopBar
          title={viewTitles[activeView]}
          subtitle={workspaceGuide?.primary_workflow_title}
          healthStatus={backendHealth?.database_status}
        >
          <MobileMenuButton
            onClick={() => setMobileMenuOpen((open) => !open)}
            isOpen={mobileMenuOpen}
          />
        </TopBar>

          {errorMessage ? <div className="error-banner" role="alert" aria-live="assertive">{errorMessage}</div> : null}

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
                        <MetricCard
                          label="Investigation leads"
                          tone={
                            activeInvestigation.investigation_leads.length > 0
                              ? "critical"
                              : "neutral"
                          }
                          value={String(activeInvestigation.investigation_leads.length)}
                        />
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
                          tone="warning"
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
                                    <span className={`risk-chip ${lead.severity}`}>
                                      {lead.severity}
                                    </span>
                                  </div>
                                  <p>{lead.hypothesis}</p>
                                  <p className="muted-copy">{lead.narrative}</p>
                                  {lead.entities.length > 0 ? (
                                    <span className="signal-meta">
                                      {lead.entities
                                        .slice(0, 4)
                                        .map((entity) => entity.display_name)
                                        .join(" · ")}
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
                          ? "Running investigation..."
                          : "Run investigation"}
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
          )}

          {activeView === "analyze" && (
            <section className="dashboard-view-stack">
              <section className="content-card overview-hero">
                <div>
                  <p className="eyebrow">
                    {workspaceGuide?.primary_workflow_title ?? "Primary Workflow"}
                  </p>
                  <h2>Turn uploaded transaction data into actionable risk insights.</h2>
                  <p className="muted-copy">
                    Upload a CSV file, run statistical and behavioral analysis, review the
                    generated alerts, and create a case when the evidence supports it.
                  </p>
                </div>
                <div className="llm-note compact">
                  <strong>AI disclaimer</strong>
                  <p>
                    {workspaceGuide?.llm_positioning_note ??
                      "AI-generated summaries explain scored findings. They do not change scores or thresholds."}
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

                  <label className="upload-zone" htmlFor="dataset-upload">
                    <p>
                      <strong>Upload a transaction CSV</strong>
                    </p>
                    <p className="muted-copy">
                      Required columns: <code>transaction_id</code>, <code>account_id</code>,{" "}
                      <code>amount</code>, <code>timestamp</code>
                    </p>
                    <span className="upload-zone-cta">
                      {isUploading ? "Uploading…" : "Choose file or drag & drop"}
                    </span>
                    <input
                      accept=".csv"
                      disabled={isUploading}
                      id="dataset-upload"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void handleUploadDataset(file);
                        event.target.value = "";
                      }}
                      type="file"
                    />
                  </label>

                  {datasets.length === 0 ? (
                    <div className="empty-state">
                      No datasets yet. Upload a CSV file to get started.
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
                        This dataset is waiting for statistical and behavioral analysis.
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
                        Analysis failed. Check the error details and try uploading a corrected file.
                      </p>
                    </div>
                  ) : null}

                  {selectedDataset?.status === "analyzing" ? (
                    <div className="stack" style={{ padding: 20 }}>
                      <SkeletonCard />
                      <SkeletonMetricRow count={3} />
                    </div>
                  ) : null}

                  {selectedDataset?.status === "completed" &&
                  isLoadingAnalysisDetail &&
                  !activeAnalysisMatchesSelection ? (
                    <div className="stack" style={{ padding: 20 }}>
                      <SkeletonMetricRow count={4} />
                      <SkeletonList rows={3} />
                    </div>
                  ) : null}

                  {selectedDataset?.status === "completed" &&
                  analysisDetailError &&
                  !activeAnalysisMatchesSelection ? (
                    <div className="error-banner">{analysisDetailError}</div>
                  ) : null}

                  {!selectedDataset ? (
                    <div className="empty-state">
                      Select a dataset from the queue to view its analysis.
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
                            <RiskGauge
                              score={activeAnalysis.risk_score}
                              level={activeAnalysis.risk_level}
                              label="Risk Score"
                            />
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
                          <MetricCard
                            label="Investigation leads"
                            tone={
                              activeAnalysis.investigation_leads.length > 0 ? "critical" : "neutral"
                            }
                            value={String(activeAnalysis.investigation_leads.length)}
                          />
                          <MetricCard
                            label="Behavioral insights"
                            tone={
                              activeAnalysis.behavioral_insights.length > 0 ? "warning" : "neutral"
                            }
                            value={String(activeAnalysis.behavioral_insights.length)}
                          />
                          <MetricCard
                            label="Graph factor"
                            tone={
                              (activeAnalysis.graph_analysis?.risk_amplification_factor ?? 1) > 1.15
                                ? "critical"
                                : "neutral"
                            }
                            value={`${
                              activeAnalysis.graph_analysis?.risk_amplification_factor.toFixed(2) ??
                              "1.00"
                            }x`}
                          />
                        </div>

                        <div className="action-bar">
                          <button
                            className="primary-button"
                            onClick={handleCreateCaseFromAnalysis}
                            type="button"
                          >
                            Create linked case from analysis
                          </button>
                        </div>
                      </section>

                      {analysisDetailError ? <div className="error-banner">{analysisDetailError}</div> : null}

                      <div className="analysis-summary-grid">
                        <section className="stack">
                          <section className="content-card">
                            <div className="mini-header">
                              <span>Investigation Leads</span>
                              <span>{activeAnalysis.investigation_leads.length}</span>
                            </div>
                            <p className="muted-copy" style={{ margin: "8px 0" }}>
                              Hypotheses generated from the analysis findings, grouped into
                              actionable review paths.
                            </p>
                            {activeAnalysis.investigation_leads.length > 0 ? (
                              <div className="stack">
                                {activeAnalysis.investigation_leads.map((lead) => (
                                  <article key={lead.lead_id} className="signal-card">
                                    <div className="signal-card-top">
                                      <strong>{lead.title}</strong>
                                      <span className={`risk-chip ${lead.severity}`}>
                                        {lead.severity}
                                      </span>
                                    </div>
                                    <p>{lead.hypothesis}</p>
                                    <p className="muted-copy">{lead.narrative}</p>
                                    {lead.entities.length > 0 ? (
                                      <span className="signal-meta">
                                        {lead.entities
                                          .slice(0, 4)
                                          .map((entity) => entity.display_name)
                                          .join(" · ")}
                                      </span>
                                    ) : null}
                                    {lead.recommended_actions.length > 0 ? (
                                      <span className="signal-meta">
                                        Next: {lead.recommended_actions.slice(0, 2).join(" / ")}
                                      </span>
                                    ) : null}
                                  </article>
                                ))}
                              </div>
                            ) : (
                              <div className="empty-state">
                                No investigation leads were generated. Review the anomalies below
                                for details.
                              </div>
                            )}
                          </section>

                          <section className="content-card">
                            <div className="mini-header">
                              <span>Benford&apos;s Law</span>
                              <span>
                                p={activeAnalysis.benford_p_value.toFixed(4)}
                              </span>
                            </div>
                            <p className="muted-copy" style={{ margin: "8px 0" }}>
                              Leading-digit distribution compared against expected frequencies.
                              Significant deviations may indicate manipulated data.
                            </p>
                            <BenfordChart digits={activeAnalysis.benford_digits} />
                          </section>

                          {activeAnalysis.behavioral_insights.length > 0 ? (
                            <section className="content-card">
                              <div className="mini-header">
                                <span>Behavioral Insights</span>
                                <span>{activeAnalysis.behavioral_insights.length}</span>
                              </div>
                              <div className="stack">
                                {activeAnalysis.behavioral_insights.map((insight) => (
                                  <article key={insight.insight_id} className="signal-card">
                                    <div className="signal-card-top">
                                      <strong>{insight.title}</strong>
                                      <span className={`risk-chip ${insight.severity}`}>
                                        {insight.severity}
                                      </span>
                                    </div>
                                    <p>{insight.narrative}</p>
                                    {insight.entities.length > 0 ? (
                                      <span className="signal-meta">
                                        {insight.entities
                                          .slice(0, 4)
                                          .map((entity) => entity.display_name)
                                          .join(" · ")}
                                      </span>
                                    ) : null}
                                  </article>
                                ))}
                              </div>
                            </section>
                          ) : null}

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

                          {activeAnalysis.graph_analysis ? (
                            <section className="content-card">
                              <div className="mini-header">
                                <span>Relationship Graph</span>
                                <span>
                                  {activeAnalysis.graph_analysis.risk_amplification_factor.toFixed(2)}x
                                </span>
                              </div>
                              <div className="metrics-grid">
                                <MetricCard
                                  label="Components"
                                  tone="neutral"
                                  value={String(activeAnalysis.graph_analysis.connected_components)}
                                />
                                <MetricCard
                                  label="Density"
                                  tone={
                                    activeAnalysis.graph_analysis.density > 0.2
                                      ? "warning"
                                      : "neutral"
                                  }
                                  value={activeAnalysis.graph_analysis.density.toFixed(3)}
                                />
                                <MetricCard
                                  label="Communities"
                                  tone="neutral"
                                  value={String(activeAnalysis.graph_analysis.community_count)}
                                />
                                <MetricCard
                                  label="Top hub degree"
                                  tone="neutral"
                                  value={String(activeAnalysis.graph_analysis.highest_degree_score)}
                                />
                              </div>
                              {activeAnalysis.graph_analysis.hub_entities.length > 0 ? (
                                <div className="stack" style={{ marginTop: 8 }}>
                                  {activeAnalysis.graph_analysis.hub_entities.map((hub) => (
                                    <article
                                      key={`${hub.entity_type}-${hub.entity_id}`}
                                      className="transaction-row"
                                    >
                                      <div>
                                        <strong>{hub.display_name}</strong>
                                        <p>{hub.entity_type} hub in the inferred relationship graph</p>
                                      </div>
                                      <div className="transaction-meta">
                                        <strong>{hub.entity_type}</strong>
                                      </div>
                                    </article>
                                  ))}
                                </div>
                              ) : null}
                            </section>
                          ) : null}

                          {activeAnalysis.velocity_spikes.length > 0 ? (
                            <section className="content-card">
                              <div className="mini-header">
                                <span>Velocity Windows</span>
                                <span>{activeAnalysis.velocity_spikes.length}</span>
                              </div>
                              <VelocityChart spikes={activeAnalysis.velocity_spikes} />
                              <div className="stack" style={{ marginTop: 8 }}>
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

                        <AnalysisSummaryCard
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
              selectedCaseId={selectedCaseId}
              activeCaseDetail={activeCaseDetail}
              isLoadingCaseDetail={isLoadingCaseDetail}
              caseDetailError={caseDetailError}
              isSubmittingCaseComment={isSubmittingCaseComment}
              dateFormatter={dateFormatter}
              onSelectCase={handleCaseSelection}
              onAddCaseComment={handleAddCaseComment}
              onResolveCase={handleResolveCase}
            />
          )}

          {activeView === "alerts" && (
            <AlertsSection
              alerts={alerts}
              dateFormatter={dateFormatter}
              onAcknowledgeAlert={handleAcknowledgeAlert}
              onCreateCaseFromAlert={handleCreateCaseFromAlert}
            />
          )}

          {activeView === "audit" && operator.role === "admin" ? (
            <AuditSection auditEvents={auditEvents} dateFormatter={dateFormatter} />
          ) : null}
      </main>
    </div>
  );
}
