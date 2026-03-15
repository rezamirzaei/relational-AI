"use client";

import {
  BenfordChart,
  RiskGauge,
  VelocityChart,
} from "@/components/charts";
import {
  AnalysisSummaryCard,
  MetricCard,
} from "@/components/dashboard-sections";
import { SkeletonCard, SkeletonList, SkeletonMetricRow } from "@/components/skeletons";
import type {
  AnalysisExplanation,
  AnalysisResponse,
  DashboardStats,
  DatasetInfo,
  WorkspaceGuide,
} from "@/lib/contracts";

type AnalyzeViewProps = {
  workspaceGuide: WorkspaceGuide | null;
  dashboardStats: DashboardStats | null;
  datasets: DatasetInfo[];
  selectedDatasetId: string | null;
  selectedDataset: DatasetInfo | null;
  activeAnalysis: AnalysisResponse["analysis"] | null;
  activeAnalysisMatchesSelection: boolean;
  analysisExplanation: AnalysisExplanation | null;
  isUploading: boolean;
  isAnalyzing: boolean;
  isLoadingAnalysisDetail: boolean;
  analysisDetailError: string | null;
  analysisExplanationError: string | null;
  currencyFormatter: Intl.NumberFormat;
  dateFormatter: Intl.DateTimeFormat;
  onUploadDataset: (file: File) => Promise<void>;
  onDatasetSelection: (dataset: DatasetInfo) => Promise<void>;
  onAnalyzeDataset: (datasetId: string) => Promise<void>;
  onCreateCaseFromAnalysis: () => void;
};

export function AnalyzeView({
  workspaceGuide,
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
  currencyFormatter,
  dateFormatter,
  onUploadDataset,
  onDatasetSelection,
  onAnalyzeDataset,
  onCreateCaseFromAnalysis,
}: AnalyzeViewProps) {
  return (
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
                if (file) void onUploadDataset(file);
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
                      onClick={() => void onDatasetSelection(dataset)}
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
                          onClick={() => void onAnalyzeDataset(dataset.dataset_id)}
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
                            onClick={() => void onDatasetSelection(dataset)}
                            type="button"
                          >
                            View analysis
                          </button>
                          <button
                            className="small-button"
                            disabled={isAnalyzing}
                            onClick={() => void onAnalyzeDataset(dataset.dataset_id)}
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
                onClick={() => void onAnalyzeDataset(selectedDataset.dataset_id)}
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
                  <MetricCard label="Transactions" tone="neutral" value={activeAnalysis.total_transactions.toLocaleString()} />
                  <MetricCard label="Anomalies" tone={activeAnalysis.total_anomalies > 0 ? "critical" : "neutral"} value={String(activeAnalysis.total_anomalies)} />
                  <MetricCard label="Outliers" tone={activeAnalysis.outlier_count > 0 ? "warning" : "neutral"} value={`${activeAnalysis.outlier_count} (${activeAnalysis.outlier_pct}%)`} />
                  <MetricCard label="Velocity spikes" tone={activeAnalysis.velocity_spikes.length > 0 ? "warning" : "neutral"} value={String(activeAnalysis.velocity_spikes.length)} />
                  <MetricCard label="Investigation leads" tone={activeAnalysis.investigation_leads.length > 0 ? "critical" : "neutral"} value={String(activeAnalysis.investigation_leads.length)} />
                  <MetricCard label="Behavioral insights" tone={activeAnalysis.behavioral_insights.length > 0 ? "warning" : "neutral"} value={String(activeAnalysis.behavioral_insights.length)} />
                  <MetricCard label="Graph factor" tone={(activeAnalysis.graph_analysis?.risk_amplification_factor ?? 1) > 1.15 ? "critical" : "neutral"} value={`${activeAnalysis.graph_analysis?.risk_amplification_factor.toFixed(2) ?? "1.00"}x`} />
                </div>

                <div className="action-bar">
                  <button className="primary-button" onClick={onCreateCaseFromAnalysis} type="button">
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
                      Hypotheses generated from the analysis findings, grouped into actionable review paths.
                    </p>
                    {activeAnalysis.investigation_leads.length > 0 ? (
                      <div className="stack">
                        {activeAnalysis.investigation_leads.map((lead) => (
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
                        No investigation leads were generated. Review the anomalies below for details.
                      </div>
                    )}
                  </section>

                  <section className="content-card">
                    <div className="mini-header">
                      <span>Benford&apos;s Law</span>
                      <span>p={activeAnalysis.benford_p_value.toFixed(4)}</span>
                    </div>
                    <p className="muted-copy" style={{ margin: "8px 0" }}>
                      Leading-digit distribution compared against expected frequencies. Significant deviations may indicate manipulated data.
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
                              <span className={`risk-chip ${insight.severity}`}>{insight.severity}</span>
                            </div>
                            <p>{insight.narrative}</p>
                            {insight.entities.length > 0 ? (
                              <span className="signal-meta">
                                {insight.entities.slice(0, 4).map((entity) => entity.display_name).join(" · ")}
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
                            <span className={`risk-chip ${anomaly.severity}`}>{anomaly.severity}</span>
                          </div>
                          <p>{anomaly.description}</p>
                          <span className="signal-meta">
                            {anomaly.anomaly_type} on {anomaly.affected_entity_type} {anomaly.affected_entity_id}
                          </span>
                        </article>
                      ))}
                    </div>
                  </section>

                  {activeAnalysis.graph_analysis ? (
                    <section className="content-card">
                      <div className="mini-header">
                        <span>Relationship Graph</span>
                        <span>{activeAnalysis.graph_analysis.risk_amplification_factor.toFixed(2)}x</span>
                      </div>
                      <div className="metrics-grid">
                        <MetricCard label="Components" tone="neutral" value={String(activeAnalysis.graph_analysis.connected_components)} />
                        <MetricCard label="Density" tone={activeAnalysis.graph_analysis.density > 0.2 ? "warning" : "neutral"} value={activeAnalysis.graph_analysis.density.toFixed(3)} />
                        <MetricCard label="Communities" tone="neutral" value={String(activeAnalysis.graph_analysis.community_count)} />
                        <MetricCard label="Top hub degree" tone="neutral" value={String(activeAnalysis.graph_analysis.highest_degree_score)} />
                      </div>
                      {activeAnalysis.graph_analysis.hub_entities.length > 0 ? (
                        <div className="stack" style={{ marginTop: 8 }}>
                          {activeAnalysis.graph_analysis.hub_entities.map((hub) => (
                            <article key={`${hub.entity_type}-${hub.entity_id}`} className="transaction-row">
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
                              <strong>{spike.entity_type} {spike.entity_id}</strong>
                              <p>
                                {spike.transaction_count} transactions for{" "}
                                {currencyFormatter.format(spike.total_amount)}
                              </p>
                            </div>
                            <div className="transaction-meta">
                              <strong>{spike.z_score.toFixed(1)}σ</strong>
                              <span>{dateFormatter.format(new Date(spike.window_start))}</span>
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
  );
}
