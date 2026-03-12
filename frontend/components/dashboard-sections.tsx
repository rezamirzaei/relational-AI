import type { FormEvent } from "react";

import type {
  AuditEvent,
  DashboardStats,
  FraudAlert,
  FraudCase,
  HealthResponse,
  OperatorPrincipal,
} from "@/lib/contracts";

export type ActiveView = "overview" | "investigate" | "analyze" | "cases" | "alerts" | "audit";

type MetricCardProps = {
  label: string;
  tone: "critical" | "good" | "neutral" | "warning";
  value: string;
};

export function MetricCard({ label, tone, value }: MetricCardProps) {
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

export function StatusPill({ label, tone }: StatusPillProps) {
  return <span className={`status-pill ${tone}`}>{label}</span>;
}

type DashboardHeaderProps = {
  backendHealth: HealthResponse | null;
  operator: OperatorPrincipal | null;
};

export function DashboardHeader({ backendHealth, operator }: DashboardHeaderProps) {
  return (
    <header className="ops-header">
      <div>
        <div className="eyebrow">Dataset Fraud Triage Workspace</div>
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
  );
}

type SignedOutPanelProps = {
  backendHealth: HealthResponse | null;
  isAuthenticating: boolean;
  loginError: string | null;
  password: string;
  showBootstrapCredentials: boolean;
  username: string;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUsernameChange: (value: string) => void;
};

export function SignedOutPanel({
  backendHealth,
  isAuthenticating,
  loginError,
  password,
  showBootstrapCredentials,
  username,
  onPasswordChange,
  onSubmit,
  onUsernameChange,
}: SignedOutPanelProps) {
  return (
    <>
      <section className="hero-panel">
        <div className="hero-copy-block">
          <p className="hero-copy">
            Upload transaction data, detect anomalies automatically, and move the suspicious
            findings into persistent alerts and cases. Reference scenarios are still available,
            but the main workflow now starts from your own data.
          </p>
          <div className="hero-ribbon">
            <span>CSV data upload</span>
            <span>Benford&apos;s Law</span>
            <span>Persistent alerts</span>
            <span>Case triage</span>
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
            <p>Reference scenarios available for validation workflows.</p>
          </article>
          <article className="hero-stat-card">
            <span className="hero-label">Operators</span>
            <strong>{backendHealth?.seeded_operators ?? 0}</strong>
            <p>Bootstrap operator accounts.</p>
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
      </section>
    </>
  );
}

type DashboardNavProps = {
  activeView: ActiveView;
  alerts: FraudAlert[];
  cases: FraudCase[];
  operator: OperatorPrincipal;
  onLogout: () => void;
  onViewChange: (view: ActiveView) => void;
};

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
      ? ["overview", "investigate", "analyze", "cases", "alerts", "audit"]
      : ["overview", "investigate", "analyze", "cases", "alerts"];

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
            {view === "overview"
              ? "Dashboard"
              : view === "investigate"
                ? "Reference Scenarios"
                : view === "analyze"
                  ? "Analyze Data"
                  : view === "audit"
                    ? "Audit Trail"
                    : view.charAt(0).toUpperCase() + view.slice(1)}
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

type OverviewSectionProps = {
  dashboardStats: DashboardStats | null;
  datasetsCount: number;
  scenariosCount: number;
};

export function OverviewSection({
  dashboardStats,
  datasetsCount,
  scenariosCount,
}: OverviewSectionProps) {
  return (
    <section className="dashboard-overview">
      <div className="stats-grid">
        <MetricCard
          label="Total Scenarios"
          tone="neutral"
          value={String(dashboardStats?.total_scenarios ?? scenariosCount)}
        />
        <MetricCard
          label="Datasets Uploaded"
          tone="neutral"
          value={String(dashboardStats?.total_datasets ?? datasetsCount)}
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
          label="Active Cases"
          tone="warning"
          value={String(dashboardStats?.open_cases ?? 0)}
        />
        <MetricCard
          label="Pending Alerts"
          tone="critical"
          value={String(dashboardStats?.unacknowledged_alerts ?? 0)}
        />
        <MetricCard
          label="Total Cases"
          tone="neutral"
          value={String(dashboardStats?.total_cases ?? 0)}
        />
        <MetricCard
          label="Avg Risk Score"
          tone="warning"
          value={`${dashboardStats?.avg_risk_score?.toFixed(0) ?? 0}/100`}
        />
      </div>

      {dashboardStats && Object.keys(dashboardStats.cases_by_status).length > 0 ? (
        <div className="insight-grid">
          <section className="content-card">
            <div className="mini-header">
              <span>Cases by Status</span>
              <span>{dashboardStats.total_cases}</span>
            </div>
            <div className="bar-chart">
              {Object.entries(dashboardStats.cases_by_status).map(([status, count]) => (
                <div key={status} className="bar-row">
                  <span className="bar-label">{status}</span>
                  <div className="bar-track">
                    <div
                      className={`bar-fill ${status === "open" || status === "investigating" ? "warning" : "good"}`}
                      style={{
                        width: `${Math.max(
                          8,
                          (count / Math.max(1, dashboardStats.total_cases)) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="bar-value">{count}</span>
                </div>
              ))}
            </div>
          </section>
          <section className="content-card">
            <div className="mini-header">
              <span>Alerts by Severity</span>
              <span>{dashboardStats.total_alerts}</span>
            </div>
            <div className="bar-chart">
              {Object.entries(dashboardStats.alerts_by_severity).map(([severity, count]) => (
                <div key={severity} className="bar-row">
                  <span className="bar-label">{severity}</span>
                  <div className="bar-track">
                    <div
                      className={`bar-fill ${severity}`}
                      style={{
                        width: `${Math.max(
                          8,
                          (count / Math.max(1, dashboardStats.total_alerts)) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="bar-value">{count}</span>
                </div>
              ))}
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
              <article key={index} className="transaction-row">
                <div>
                  <strong>{event.event_type}</strong>
                  <p>{event.description}</p>
                </div>
                <div className="transaction-meta">
                  <span>{new Intl.DateTimeFormat("en-US", {
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    month: "short",
                  }).format(new Date(event.occurred_at))}</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {!dashboardStats || dashboardStats.total_cases === 0 ? (
        <section className="content-card emphasis-card">
          <div className="mini-header">
            <span>Getting Started</span>
            <span>Guide</span>
          </div>
          <div className="action-stack">
            <article className="action-item">
              <span className="action-marker" />
              <p>
                Start in <strong>Analyze Data</strong> and upload a transaction dataset.
              </p>
            </article>
            <article className="action-item">
              <span className="action-marker" />
              <p>
                High-risk analyses <strong>auto-generate alerts</strong> for triage.
              </p>
            </article>
            <article className="action-item">
              <span className="action-marker" />
              <p>
                Create a <strong>case</strong> from the dataset analysis to track resolution.
              </p>
            </article>
            <article className="action-item">
              <span className="action-marker" />
              <p>
                Use <strong>Reference Scenarios</strong> when you want to validate the rule
                engine or train analysts.
              </p>
            </article>
          </div>
        </section>
      ) : null}
    </section>
  );
}

type CasesSectionProps = {
  cases: FraudCase[];
  dateFormatter: Intl.DateTimeFormat;
  onResolveCase: (caseId: string) => void;
};

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
        <div className="empty-state">No cases yet. Investigate a scenario and create one.</div>
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

type AlertsSectionProps = {
  alerts: FraudAlert[];
  dateFormatter: Intl.DateTimeFormat;
  onAcknowledgeAlert: (alertId: string) => void;
};

export function AlertsSection({
  alerts,
  dateFormatter,
  onAcknowledgeAlert,
}: AlertsSectionProps) {
  return (
    <section className="surface" style={{ padding: 24 }}>
      <div className="section-header">
        <span>Fraud Alerts</span>
        <span>{alerts.length} total</span>
      </div>
      {alerts.length === 0 ? (
        <div className="empty-state">
          No alerts yet. They are auto-generated when investigations detect risk.
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

type AuditSectionProps = {
  auditEvents: AuditEvent[];
  dateFormatter: Intl.DateTimeFormat;
};

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
