"use client";

import { useState } from "react";

import { AnalyzeView } from "@/components/analyze-view";
import {
  AlertsSection,
  AuditSection,
  CasesSection,
  DashboardHeader,
  OverviewSection,
  SignedOutPanel,
} from "@/components/dashboard-sections";
import { InvestigateView } from "@/components/investigate-view";
import { MobileMenuButton, Sidebar, TopBar, type ActiveView } from "@/components/sidebar";
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
    draftScenarioJson,
    draftScenarioError,
    activeInvestigationCanCreateCase,
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
    setDraftScenarioJson,
    handleLogin,
    handleLogout,
    handleScenarioSelection,
    handleRunSelectedScenario,
    handleRunDraftScenario,
    handleLoadScenarioIntoDraft,
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
            <InvestigateView
              isPending={isPending}
              scenarios={scenarios}
              selectedScenarioId={selectedScenarioId}
              selectedScenario={selectedScenario}
              activeInvestigation={activeInvestigation}
              activeInvestigationMatchesSelection={activeInvestigationMatchesSelection}
              visibleScenarios={visibleScenarios}
              searchQuery={searchQuery}
              deferredSignals={deferredSignals}
              draftScenarioJson={draftScenarioJson}
              draftScenarioError={draftScenarioError}
              activeInvestigationCanCreateCase={activeInvestigationCanCreateCase}
              backendHealth={backendHealth}
              currencyFormatter={currencyFormatter}
              dateFormatter={dateFormatter}
              onSearchQueryChange={setSearchQuery}
              onDraftScenarioJsonChange={setDraftScenarioJson}
              onScenarioSelection={handleScenarioSelection}
              onRunSelectedScenario={handleRunSelectedScenario}
              onRunDraftScenario={handleRunDraftScenario}
              onLoadScenarioIntoDraft={handleLoadScenarioIntoDraft}
              onCreateCase={handleCreateCase}
            />
          )}

          {activeView === "analyze" && (
            <AnalyzeView
              workspaceGuide={workspaceGuide}
              dashboardStats={dashboardStats}
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              selectedDataset={selectedDataset}
              activeAnalysis={activeAnalysis}
              activeAnalysisMatchesSelection={activeAnalysisMatchesSelection}
              analysisExplanation={analysisExplanation}
              isUploading={isUploading}
              isAnalyzing={isAnalyzing}
              isLoadingAnalysisDetail={isLoadingAnalysisDetail}
              analysisDetailError={analysisDetailError}
              analysisExplanationError={analysisExplanationError}
              currencyFormatter={currencyFormatter}
              dateFormatter={dateFormatter}
              onUploadDataset={handleUploadDataset}
              onDatasetSelection={handleDatasetSelection}
              onAnalyzeDataset={handleAnalyzeDataset}
              onCreateCaseFromAnalysis={handleCreateCaseFromAnalysis}
            />
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
