import type { FormEvent } from "react";

import {
  RiskDonutChart,
  SeverityBarChart,
  StatusBarChart,
} from "@/components/charts";
import type { ActiveView } from "@/components/sidebar";
import type {
  AnalysisExplanation,
  AuditEvent,
  DashboardStats,
  FraudAlert,
  FraudCase,
  HealthResponse,
  OperatorPrincipal,
  WorkspaceGuide,
} from "@/lib/contracts";

export type { ActiveView };

type MetricCardProps = {
  label: string;
  tone: "critical" | "good" | "neutral" | "warning";
  value: string;
};

type StatusPillProps = {
  label: string;
  tone: "critical" | "good" | "neutral" | "warning";
};

type DashboardHeaderProps = {
  backendHealth: HealthResponse | null;
  operator: OperatorPrincipal | null;
  workspaceGuide: WorkspaceGuide | null;
};

type SignedOutPanelProps = {
  backendHealth: HealthResponse | null;
  isAuthenticating: boolean;
  loginError: string | null;
  password: string;
  showBootstrapCredentials: boolean;
  username: string;
  workspaceGuide: WorkspaceGuide | null;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUsernameChange: (value: string) => void;
};

type DashboardNavProps = {
  activeView: ActiveView;
  alerts: FraudAlert[];
  cases: FraudCase[];
  operator: OperatorPrincipal;
  onLogout: () => void;
  onViewChange: (view: ActiveView) => void;
};

type OverviewSectionProps = {
  dashboardStats: DashboardStats | null;
  datasetsCount: number;
  scenariosCount: number;
  workspaceGuide: WorkspaceGuide | null;
  onViewChange: (view: ActiveView) => void;
};

type CasesSectionProps = {
  cases: FraudCase[];
  dateFormatter: Intl.DateTimeFormat;
  onResolveCase: (caseId: string) => void;
};

type AlertsSectionProps = {
  alerts: FraudAlert[];
  dateFormatter: Intl.DateTimeFormat;
  onAcknowledgeAlert: (alertId: string) => void;
  onCreateCaseFromAlert: (alertId: string) => void;
};

type AuditSectionProps = {
  auditEvents: AuditEvent[];
  dateFormatter: Intl.DateTimeFormat;
};

type AnalysisCopilotCardProps = {
  explanation: AnalysisExplanation | null;
  isLoading: boolean;
  loadError: string | null;
};

const activityDateFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
});

export function MetricCard({ label, tone, value }: MetricCardProps) {
  return (
    <article className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export function StatusPill({ label, tone }: StatusPillProps) {
  return <span className={`status-pill ${tone}`}>{label}</span>;
}

export function DashboardHeader({
  backendHealth,
  operator,
  workspaceGuide,
}: DashboardHeaderProps) {
  return (
    <header className="ops-header">
      <div>
        <div className="eyebrow">
          {workspaceGuide?.primary_workflow_title ?? "Dataset Fraud Triage Workspace"}
        </div>
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
          label={`providers ${backendHealth?.provider_status ?? "unknown"}`}
          tone={backendHealth?.provider_status === "ready" ? "good" : "warning"}
        />
        <StatusPill
          label={operator?.role ?? "signed-out"}
          tone={operator ? "neutral" : "warning"}
        />
      </div>
    </header>
  );
}

export function SignedOutPanel({
  backendHealth,
  isAuthenticating,
  loginError,
  password,
  showBootstrapCredentials,
  username,
  workspaceGuide,
  onPasswordChange,
  onSubmit,
  onUsernameChange,
}: SignedOutPanelProps) {
  return (
    <>
      <section className="hero-panel">
        <div className="hero-copy-block">
          <p className="eyebrow">{workspaceGuide?.primary_workflow_title ?? "Primary Workflow"}</p>
          <h2>Fraud triage starts with real transaction data.</h2>
          <p className="hero-copy">
            {workspaceGuide?.primary_workflow_summary ??
              "Upload transaction data, run statistical and behavioral analysis, turn the strongest findings into investigation leads, and open cases only when the evidence supports it."}
          </p>
          <div className="hero-ribbon">
            <span>Upload</span>
            <span>Analyze</span>
            <span>Alert</span>
            <span>Case</span>
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
            <p>Reference scenarios reserved for validation and training.</p>
          </article>
          <article className="hero-stat-card">
            <span className="hero-label">Operators</span>
            <strong>{backendHealth?.seeded_operators ?? 0}</strong>
            <p>Bootstrap accounts available for the analyst and admin roles.</p>
          </article>
          <article className="hero-stat-card">
            <span className="hero-label">Providers</span>
            <strong>
              {backendHealth?.provider_posture.active_explanation_provider ?? "unknown"}
            </strong>
            <p>
              Text {backendHealth?.provider_posture.active_text_signal_provider ?? "unknown"}.
              Risk {backendHealth?.provider_posture.active_reasoning_provider ?? "unknown"}.
              Copilot {backendHealth?.provider_posture.active_explanation_provider ?? "unknown"}.
            </p>
          </article>
        </div>
      </section>

      <section className="surface auth-shell">
        <div className="section-header">
          <span>Operator Sign-In</span>
          <span>Required</span>
        </div>
        <form className="auth-form" onSubmit={onSubmit}>
          <label className="auth-field">
            <span>Username</span>
            <input
              aria-label="Username"
              autoComplete="username"
              name="username"
              onChange={(event) => onUsernameChange(event.target.value)}
              type="text"
              value={username}
            />
          </label>
          <label className="auth-field">
            <span>Password</span>
            <input
              aria-label="Password"
              autoComplete="current-password"
              name="password"
              onChange={(event) => onPasswordChange(event.target.value)}
              type="password"
              value={password}
            />
          </label>
          <button className="primary-button" disabled={isAuthenticating} type="submit">
            {isAuthenticating ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {loginError ? <div className="error-banner">{loginError}</div> : null}
        {showBootstrapCredentials ? (
          <div className="auth-help">
            <strong>Local bootstrap operators</strong>
            <p>`analyst / AnalystPassword123!`</p>
            <p>`admin / AdminPassword123!`</p>
          </div>
        ) : null}
        {backendHealth?.provider_posture.notes.length ? (
          <div className="llm-note">
            <strong>Provider fallback notes</strong>
            <p>{backendHealth.provider_posture.notes.join(" ")}</p>
          </div>
        ) : null}
      </section>

      {workspaceGuide ? (
        <section className="guide-grid">
          <section className="surface guide-panel">
            <div className="mini-header">
              <span>Role Stories</span>
              <span>{workspaceGuide.role_stories.length}</span>
            </div>
            <div className="story-grid">
              {workspaceGuide.role_stories.map((story) => (
                <article key={story.story_id} className="story-card">
                  <div className="story-card-top">
                    <span className="tag-pill">{story.platform_role}</span>
                    <span className="story-persona">{story.persona_name}</span>
                  </div>
                  <h3>{story.title}</h3>
                  <p className="muted-copy">{story.goal}</p>
                  <div className="story-steps">
                    {story.workflow_steps.map((step) => (
                      <article key={step} className="action-item compact">
                        <span className="action-marker" />
                        <p>{step}</p>
                      </article>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="surface guide-panel">
            <div className="mini-header">
              <span>Scoring Guardrails</span>
              <span>Deterministic</span>
            </div>
            <div className="action-stack">
              {workspaceGuide.scoring_guarantees.map((guarantee) => (
                <article key={guarantee} className="action-item">
                  <span className="action-marker" />
                  <p>{guarantee}</p>
                </article>
              ))}
            </div>
            <div className="llm-note">
              <strong>Copilot boundary</strong>
              <p>{workspaceGuide.llm_positioning_note}</p>
            </div>
          </section>
        </section>
      ) : null}
    </>
  );
}

export function DashboardNav({
  activeView,
  alerts,
  cases,
  operator,
  onLogout,
  onViewChange,
}: DashboardNavProps) {
  const newAlertsCount = alerts.filter((alert) => alert.status === "new").length;
  const activeCasesCount = cases.filter(
    (fraudCase) => fraudCase.status === "open" || fraudCase.status === "investigating",
  ).length;
  const views: ActiveView[] =
    operator.role === "admin"
      ? ["analyze", "alerts", "cases", "overview", "investigate", "audit"]
      : ["analyze", "alerts", "cases", "overview", "investigate"];

  return (
    <nav className="nav-bar">
      <div className="nav-left">
        {views.map((view) => (
          <button
            key={view}
            className={`nav-tab ${activeView === view ? "active" : ""}`}
            onClick={() => onViewChange(view)}
            type="button"
          >
            {viewLabel(view)}
            {view === "alerts" && newAlertsCount > 0 ? (
              <span className="nav-badge">{newAlertsCount}</span>
            ) : null}
            {view === "cases" && activeCasesCount > 0 ? (
              <span className="nav-badge">{activeCasesCount}</span>
            ) : null}
          </button>
        ))}
      </div>
      <div className="nav-right">
        <span className="operator-info">
          {operator.display_name} ({operator.role})
        </span>
        <button className="secondary-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </div>
    </nav>
  );
}

export function OverviewSection({
  dashboardStats,
  datasetsCount,
  scenariosCount,
  workspaceGuide,
  onViewChange,
}: OverviewSectionProps) {
  return (
    <section className="dashboard-overview">
      {workspaceGuide ? (
        <section className="content-card overview-hero">
          <div>
            <p className="eyebrow">{workspaceGuide.primary_workflow_title}</p>
            <h2>{workspaceGuide.primary_workflow_summary}</h2>
          </div>
          <div className="overview-hero-actions">
            <div className="llm-note compact">
              <strong>Next action</strong>
              <p>
                {dashboardStats?.next_recommended_action ??
                  "Upload a dataset and move it through the analysis-to-case workflow."}
              </p>
            </div>
            <button className="primary-button" onClick={() => onViewChange("analyze")} type="button">
              Open Analyze Data
            </button>
          </div>
        </section>
      ) : null}

      {dashboardStats?.workflow_stages && dashboardStats.workflow_stages.length > 0 ? (
        <section className="workflow-strip">
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

      <div className="stats-grid">
        <MetricCard
          label="Uploaded Datasets"
          tone="neutral"
          value={String(dashboardStats?.total_datasets ?? datasetsCount)}
        />
        <MetricCard
          label="Completed Analyses"
          tone="neutral"
          value={String(dashboardStats?.completed_analyses ?? 0)}
        />
        <MetricCard
          label="High-Risk Analyses"
          tone={dashboardStats?.high_risk_analyses ? "critical" : "neutral"}
          value={String(dashboardStats?.high_risk_analyses ?? 0)}
        />
        <MetricCard
          label="New Alerts"
          tone={dashboardStats?.unacknowledged_alerts ? "critical" : "neutral"}
          value={String(dashboardStats?.unacknowledged_alerts ?? 0)}
        />
        <MetricCard
          label="Open Cases"
          tone={dashboardStats?.open_cases ? "warning" : "neutral"}
          value={String(dashboardStats?.open_cases ?? 0)}
        />
        <MetricCard
          label="Transactions Analyzed"
          tone="neutral"
          value={(dashboardStats?.total_transactions_analyzed ?? 0).toLocaleString()}
        />
        <MetricCard
          label="Anomalies Found"
          tone={dashboardStats?.total_anomalies_found ? "critical" : "neutral"}
          value={String(dashboardStats?.total_anomalies_found ?? 0)}
        />
        <MetricCard
          label="Reference Scenarios"
          tone="good"
          value={String(dashboardStats?.total_scenarios ?? scenariosCount)}
        />
      </div>

      {workspaceGuide ? (
        <div className="insight-grid">
          <section className="content-card">
            <div className="mini-header">
              <span>Role Stories</span>
              <span>{workspaceGuide.role_stories.length}</span>
            </div>
            <div className="story-grid">
              {workspaceGuide.role_stories.map((story) => (
                <article key={story.story_id} className="story-card">
                  <div className="story-card-top">
                    <span className="tag-pill">{story.platform_role}</span>
                    <span className="story-persona">{story.persona_name}</span>
                  </div>
                  <h3>{story.title}</h3>
                  <p className="muted-copy">{story.goal}</p>
                  <div className="story-steps">
                    {story.workflow_steps.map((step) => (
                      <article key={step} className="action-item compact">
                        <span className="action-marker" />
                        <p>{step}</p>
                      </article>
                    ))}
                  </div>
                  <div className="story-card-foot">
                    <p>{story.success_signal}</p>
                    <button
                      className="small-button"
                      onClick={() => onViewChange(asActiveView(story.recommended_view))}
                      type="button"
                    >
                      Open {viewLabel(asActiveView(story.recommended_view))}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="content-card">
            <div className="mini-header">
              <span>Scoring Guardrails</span>
              <span>Copilot safe</span>
            </div>
            <div className="action-stack">
              {workspaceGuide.scoring_guarantees.map((guarantee) => (
                <article key={guarantee} className="action-item">
                  <span className="action-marker" />
                  <p>{guarantee}</p>
                </article>
              ))}
            </div>
            <div className="llm-note">
              <strong>LLM boundary</strong>
              <p>{workspaceGuide.llm_positioning_note}</p>
            </div>
          </section>
        </div>
      ) : null}

      {dashboardStats && Object.keys(dashboardStats.cases_by_status).length > 0 ? (
        <div className="insight-grid">
          <section className="content-card">
            <div className="mini-header">
              <span>Cases by Status</span>
              <span>{dashboardStats.total_cases}</span>
            </div>
            <StatusBarChart data={dashboardStats.cases_by_status} />
          </section>
          <section className="content-card">
            <div className="mini-header">
              <span>Alerts by Severity</span>
              <span>{dashboardStats.total_alerts}</span>
            </div>
            <SeverityBarChart data={dashboardStats.alerts_by_severity} />
          </section>
        </div>
      ) : null}

      {dashboardStats && Object.keys(dashboardStats.risk_distribution).length > 0 ? (
        <div className="insight-grid">
          <section className="content-card">
            <div className="mini-header">
              <span>Risk Distribution</span>
              <span>All analyses</span>
            </div>
            <RiskDonutChart data={dashboardStats.risk_distribution} />
          </section>
          <section className="content-card">
            <div className="mini-header">
              <span>Quick Stats</span>
              <span>Summary</span>
            </div>
            <div className="stack" style={{ marginTop: 8 }}>
              <div className="transaction-row">
                <div><strong>Avg Risk Score</strong></div>
                <div className="transaction-meta"><strong>{dashboardStats.avg_risk_score.toFixed(1)}/100</strong></div>
              </div>
              <div className="transaction-row">
                <div><strong>Critical Cases</strong></div>
                <div className="transaction-meta"><strong>{dashboardStats.critical_cases}</strong></div>
              </div>
              <div className="transaction-row">
                <div><strong>Unacknowledged Alerts</strong></div>
                <div className="transaction-meta"><strong>{dashboardStats.unacknowledged_alerts}</strong></div>
              </div>
              <div className="transaction-row">
                <div><strong>Next Action</strong></div>
                <div className="transaction-meta"><span style={{ fontSize: "0.82rem" }}>{dashboardStats.next_recommended_action}</span></div>
              </div>
            </div>
          </section>
        </div>
      ) : null}

      {dashboardStats?.recent_activity && dashboardStats.recent_activity.length > 0 ? (
        <section className="content-card">
          <div className="mini-header">
            <span>Recent Activity</span>
            <span>{dashboardStats.recent_activity.length}</span>
          </div>
          <div className="stack">
            {dashboardStats.recent_activity.map((event, index) => (
              <article key={`${event.resource_id ?? "activity"}-${index}`} className="transaction-row">
                <div>
                  <strong>{event.event_type}</strong>
                  <p>{event.description}</p>
                </div>
                <div className="transaction-meta">
                  <span>{activityDateFormatter.format(new Date(event.occurred_at))}</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}

export function CasesSection({
  cases,
  dateFormatter,
  onResolveCase,
}: CasesSectionProps) {
  return (
    <section className="surface" style={{ padding: 24 }}>
      <div className="section-header">
        <span>Fraud Cases</span>
        <span>{cases.length} total</span>
      </div>
      {cases.length === 0 ? (
        <div className="empty-state">
          No cases yet. Create one from a high-risk dataset analysis or a reference investigation.
        </div>
      ) : (
        <div className="stack">
          {cases.map((fraudCase) => (
            <article key={fraudCase.case_id} className="case-card">
              <div className="case-card-header">
                <div>
                  <span className={`risk-chip ${fraudCase.risk_level}`}>
                    {fraudCase.priority}
                  </span>
                  <span className={`status-chip ${fraudCase.status}`}>
                    {fraudCase.status}
                  </span>
                </div>
                <span className="case-date">
                  {dateFormatter.format(new Date(fraudCase.created_at))}
                </span>
              </div>
              <h3>{fraudCase.title}</h3>
              <p className="muted-copy">{fraudCase.summary}</p>
              <div className="case-card-footer">
                <span>
                  {fraudCase.source_type === "dataset"
                    ? `Dataset ${fraudCase.source_id}`
                    : `Scenario ${fraudCase.source_id}`}
                </span>
                <span>Risk: {fraudCase.risk_score}/100</span>
                <span>{fraudCase.comment_count} comments</span>
                {fraudCase.sla_deadline ? (
                  <span>SLA: {dateFormatter.format(new Date(fraudCase.sla_deadline))}</span>
                ) : null}
                {fraudCase.status !== "resolved" && fraudCase.status !== "closed" ? (
                  <button
                    className="small-button"
                    onClick={() => onResolveCase(fraudCase.case_id)}
                    type="button"
                  >
                    Resolve
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export function AlertsSection({
  alerts,
  dateFormatter,
  onAcknowledgeAlert,
  onCreateCaseFromAlert,
}: AlertsSectionProps) {
  return (
    <section className="surface" style={{ padding: 24 }}>
      <div className="section-header">
        <span>Fraud Alerts</span>
        <span>{alerts.length} total</span>
      </div>
      {alerts.length === 0 ? (
        <div className="empty-state">
          No alerts yet. High-risk dataset analyses create them automatically.
        </div>
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
                <span>
                  {alert.source_type === "dataset"
                    ? `Dataset ${alert.source_id}`
                    : `Scenario ${alert.source_id}`}
                </span>
                <span>{dateFormatter.format(new Date(alert.created_at))}</span>
                {alert.linked_case_id ? <span>Case {alert.linked_case_id}</span> : null}
                {!alert.linked_case_id &&
                alert.status !== "resolved" &&
                alert.status !== "false-positive" ? (
                  <button
                    className="small-button"
                    onClick={() => onCreateCaseFromAlert(alert.alert_id)}
                    type="button"
                  >
                    Create case
                  </button>
                ) : null}
                {alert.status === "new" ? (
                  <button
                    className="small-button"
                    onClick={() => onAcknowledgeAlert(alert.alert_id)}
                    type="button"
                  >
                    Acknowledge
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export function AuditSection({ auditEvents, dateFormatter }: AuditSectionProps) {
  return (
    <section className="surface" style={{ padding: 24 }}>
      <div className="section-header">
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
              <span>{dateFormatter.format(new Date(event.occurred_at))}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function AnalysisCopilotCard({
  explanation,
  isLoading,
  loadError,
}: AnalysisCopilotCardProps) {
  if (isLoading) {
    return (
      <section className="content-card copilot-card">
        <div className="mini-header">
          <span>Copilot Brief</span>
          <span>Loading</span>
        </div>
        <p className="muted-copy">
          Building an operator-facing explanation from the scored dataset findings.
        </p>
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="content-card copilot-card">
        <div className="mini-header">
          <span>Copilot Brief</span>
          <span>Error</span>
        </div>
        <div className="error-banner">{loadError}</div>
      </section>
    );
  }

  if (!explanation) {
    return (
      <section className="content-card copilot-card">
        <div className="mini-header">
          <span>Copilot Brief</span>
          <span>Ready</span>
        </div>
        <p className="muted-copy">
          Select or analyze a completed dataset to generate an explanation brief.
        </p>
      </section>
    );
  }

  return (
    <section className="content-card copilot-card">
      <div className="mini-header">
        <span>Copilot Brief</span>
        <span>{explanation.audience}</span>
      </div>
      <div className="stack">
        <article className="llm-note">
          <strong>{explanation.headline}</strong>
          <p>{explanation.narrative}</p>
        </article>

        <div className="insight-grid compact">
          <section className="content-card inset-card">
            <div className="mini-header">
              <span>Scored Evidence</span>
              <span>{explanation.deterministic_evidence.length}</span>
            </div>
            <div className="action-stack">
              {explanation.deterministic_evidence.map((item) => (
                <article key={item} className="action-item compact">
                  <span className="action-marker" />
                  <p>{item}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="content-card inset-card">
            <div className="mini-header">
              <span>Recommended Actions</span>
              <span>{explanation.recommended_actions.length}</span>
            </div>
            <div className="action-stack">
              {explanation.recommended_actions.map((item) => (
                <article key={item} className="action-item compact">
                  <span className="action-marker" />
                  <p>{item}</p>
                </article>
              ))}
            </div>
          </section>
        </div>

        <section className="content-card inset-card">
          <div className="mini-header">
            <span>Guardrails</span>
            <span>{explanation.provider_summary.source_of_truth}</span>
          </div>
          <div className="action-stack">
            {explanation.watchouts.map((item) => (
              <article key={item} className="action-item compact">
                <span className="action-marker" />
                <p>{item}</p>
              </article>
            ))}
          </div>
          <div className="provider-grid">
            <span>Requested</span>
            <strong>{explanation.provider_summary.requested_provider}</strong>
            <span>Active</span>
            <strong>{explanation.provider_summary.active_provider}</strong>
            <span>Source of truth</span>
            <strong>{explanation.provider_summary.source_of_truth}</strong>
          </div>
          <div className="stack">
            {explanation.provider_summary.notes.map((note) => (
              <p key={note} className="provider-note">
                {note}
              </p>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function viewLabel(view: ActiveView): string {
  switch (view) {
    case "overview":
      return "Workspace";
    case "investigate":
      return "Reference Scenarios";
    case "analyze":
      return "Analyze Data";
    case "cases":
      return "Cases";
    case "alerts":
      return "Alerts";
    case "audit":
      return "Audit Trail";
    default:
      return view;
  }
}

function asActiveView(view: string): ActiveView {
  if (
    view === "overview" ||
    view === "investigate" ||
    view === "analyze" ||
    view === "cases" ||
    view === "alerts" ||
    view === "audit"
  ) {
    return view;
  }
  return "analyze";
}
