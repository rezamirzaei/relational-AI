/**
 * Custom hook that encapsulates all Dashboard state management.
 *
 * This was extracted from the 1,296-line Dashboard component to separate
 * concerns: the hook owns data fetching, auth, and state transitions;
 * the component owns rendering.
 */

import { FormEvent, useDeferredValue, useEffect, useState, useTransition } from "react";

import {
  addCaseComment,
  analyzeDataset,
  createCaseFromAlert,
  createCaseFromAnalysis,
  createCaseFromInvestigation,
  fetchAlerts,
  fetchAnalysisExplanation,
  fetchAnalysisResult,
  fetchAuditEvents,
  fetchCase,
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
  GetCaseResponse,
  HealthResponse,
  InvestigationResponse,
  OperatorPrincipal,
  ScenarioOverview,
} from "@/lib/contracts";
import type { ActiveView } from "@/components/sidebar";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RefreshOptions = {
  alerts?: boolean;
  audit?: boolean;
  cases?: boolean;
  datasets?: boolean;
  stats?: boolean;
};

export type DashboardState = {
  // Auth
  authToken: string | null;
  operator: OperatorPrincipal | null;
  username: string;
  password: string;
  isAuthenticating: boolean;
  loginError: string | null;
  showBootstrapCredentials: boolean;

  // Navigation
  activeView: ActiveView;
  isPending: boolean;
  errorMessage: string | null;

  // Scenarios & Investigation
  scenarios: ScenarioOverview[];
  selectedScenarioId: string | null;
  selectedScenario: ScenarioOverview | null;
  investigation: InvestigationResponse | null;
  activeInvestigation: InvestigationResponse["investigation"] | null;
  activeInvestigationMatchesSelection: boolean;
  visibleScenarios: ScenarioOverview[];
  searchQuery: string;
  deferredSignals: InvestigationResponse["investigation"]["text_signals"];

  // Cases & Alerts
  cases: FraudCase[];
  selectedCaseId: string | null;
  activeCaseDetail: GetCaseResponse | null;
  isLoadingCaseDetail: boolean;
  caseDetailError: string | null;
  isSubmittingCaseComment: boolean;
  alerts: FraudAlert[];
  auditEvents: AuditEvent[];

  // Dashboard
  dashboardStats: DashboardStats | null;

  // Datasets & Analysis
  datasets: DatasetInfo[];
  selectedDatasetId: string | null;
  selectedDataset: DatasetInfo | null;
  activeAnalysis: AnalysisResultData | null;
  activeAnalysisMatchesSelection: boolean;
  analysisExplanation: AnalysisExplanation | null;
  isUploading: boolean;
  isAnalyzing: boolean;
  isLoadingAnalysisDetail: boolean;
  analysisDetailError: string | null;
  analysisExplanationError: string | null;
};

export type DashboardActions = {
  setUsername: (v: string) => void;
  setPassword: (v: string) => void;
  setActiveView: (v: ActiveView) => void;
  setSearchQuery: (v: string) => void;
  handleLogin: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleLogout: () => void;
  handleScenarioSelection: (scenarioId: string) => Promise<void>;
  handleCreateCase: () => Promise<void>;
  handleAcknowledgeAlert: (alertId: string) => Promise<void>;
  handleCaseSelection: (caseId: string) => Promise<void>;
  handleAddCaseComment: (caseId: string, body: string) => Promise<void>;
  handleResolveCase: (caseId: string) => Promise<void>;
  handleCreateCaseFromAlert: (alertId: string) => Promise<void>;
  handleUploadDataset: (file: File) => Promise<void>;
  handleDatasetSelection: (dataset: DatasetInfo) => Promise<void>;
  handleAnalyzeDataset: (datasetId: string) => Promise<void>;
  handleCreateCaseFromAnalysis: () => Promise<void>;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const tokenStorageKey = "rfi.operator-token";

function defaultViewForRole(role: OperatorPrincipal["role"]): ActiveView {
  return role === "admin" ? "overview" : "analyze";
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useDashboardState(
  backendHealth: HealthResponse | null,
  bootstrapError: string | null,
): [DashboardState, DashboardActions] {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [operator, setOperator] = useState<OperatorPrincipal | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioOverview[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [cases, setCases] = useState<FraudCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [activeCaseDetail, setActiveCaseDetail] = useState<GetCaseResponse | null>(null);
  const [isLoadingCaseDetail, setIsLoadingCaseDetail] = useState(false);
  const [caseDetailError, setCaseDetailError] = useState<string | null>(null);
  const [isSubmittingCaseComment, setIsSubmittingCaseComment] = useState(false);
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

  // Derived values
  const deferredQuery = useDeferredValue(searchQuery);
  const deferredSignals = useDeferredValue(investigation?.investigation.text_signals ?? []);
  const showBootstrapCredentials =
    backendHealth?.environment === "local" || backendHealth?.environment === "test";
  const selectedScenario =
    scenarios.find((s) => s.scenario_id === selectedScenarioId) ?? scenarios[0] ?? null;
  const activeInvestigation = investigation?.investigation ?? null;
  const activeInvestigationMatchesSelection =
    activeInvestigation?.scenario.scenario_id === selectedScenarioId;
  const selectedDataset =
    datasets.find((d) => d.dataset_id === selectedDatasetId) ?? null;
  const activeAnalysisMatchesSelection = activeAnalysis?.dataset_id === selectedDatasetId;
  const visibleScenarios = scenarios.filter((scenario) => {
    const query = deferredQuery.trim().toLowerCase();
    if (!query) return true;
    return [scenario.title, scenario.industry, scenario.summary, scenario.hypothesis, ...scenario.tags]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  // Session restore
  useEffect(() => {
    const savedToken = window.localStorage.getItem(tokenStorageKey);
    if (!savedToken) return;
    void hydrateOperatorSession(savedToken);
  }, []);

  useEffect(() => {
    if (!authToken || activeView !== "cases" || !selectedCaseId || isLoadingCaseDetail) return;
    if (activeCaseDetail?.case.case_id === selectedCaseId) return;
    void loadCaseDetail(authToken, selectedCaseId);
  }, [activeCaseDetail?.case.case_id, activeView, authToken, isLoadingCaseDetail, selectedCaseId]);

  // -----------------------------------------------------------------------
  // Internal helpers
  // -----------------------------------------------------------------------

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
      nextDatasets.find((d) => d.status === "completed") ?? nextDatasets[0] ?? null;

    setOperator(principal);
    setScenarios(scenarioCatalog.scenarios);
    setSelectedScenarioId(firstScenarioId);
    setInvestigation(null);
    setAuditEvents(nextAuditEvents);
    setDashboardStats(nextStats);
    setCases(nextCases);
    setSelectedCaseId(nextCases[0]?.case_id ?? null);
    setActiveCaseDetail(null);
    setCaseDetailError(null);
    setAlerts(nextAlerts);
    setDatasets(nextDatasets);
    setSelectedDatasetId(preferredDataset?.dataset_id ?? null);
    setActiveAnalysis(null);
    setAnalysisExplanation(null);
    setAnalysisDetailError(null);
    setAnalysisExplanationError(null);
    setActiveView(defaultViewForRole(principal.role));

    if (preferredDataset?.status === "completed") {
      await loadDatasetDetail(token, preferredDataset.dataset_id, principal.role);
    }
  }

  async function refreshWorkspaceSlices(
    token: string,
    {
      alerts: doAlerts = false,
      audit = false,
      cases: doCases = false,
      datasets: doDatasets = false,
      stats = false,
    }: RefreshOptions,
  ): Promise<void> {
    const shouldRefreshAudit = audit && operator?.role === "admin";
    const [alertsResult, auditResult, casesResult, datasetsResult, statsResult] =
      await Promise.allSettled([
        doAlerts ? fetchAlerts(token) : Promise.resolve(null),
        shouldRefreshAudit ? fetchAuditEvents(token) : Promise.resolve(null),
        doCases ? fetchCases(token) : Promise.resolve(null),
        doDatasets ? fetchDatasets(token) : Promise.resolve(null),
        stats ? fetchDashboardStats(token) : Promise.resolve(null),
      ] as const);

    if (alertsResult.status === "fulfilled" && alertsResult.value) setAlerts(alertsResult.value.alerts);
    if (auditResult.status === "fulfilled" && auditResult.value) setAuditEvents(auditResult.value.events);
    if (casesResult.status === "fulfilled" && casesResult.value) {
      const nextCases = casesResult.value.cases;
      setCases(nextCases);
      setSelectedCaseId((currentCaseId) => {
        if (currentCaseId && nextCases.some((item) => item.case_id === currentCaseId)) {
          return currentCaseId;
        }
        return nextCases[0]?.case_id ?? null;
      });
      if (nextCases.length === 0) {
        setActiveCaseDetail(null);
        setCaseDetailError(null);
      }
    }
    if (datasetsResult.status === "fulfilled" && datasetsResult.value) setDatasets(datasetsResult.value.datasets);
    if (statsResult.status === "fulfilled" && statsResult.value) setDashboardStats(statsResult.value.stats);
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

  async function loadCaseDetail(token: string, caseId: string) {
    setSelectedCaseId(caseId);
    setIsLoadingCaseDetail(true);
    setCaseDetailError(null);
    setErrorMessage(null);

    try {
      setActiveCaseDetail(await fetchCase(token, caseId));
    } catch (error) {
      setActiveCaseDetail(null);
      setCaseDetailError(error instanceof Error ? error.message : "Could not load case details.");
    } finally {
      setIsLoadingCaseDetail(false);
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
    if (!knownAnalysis) setActiveAnalysis(null);
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
      setAnalysisDetailError(
        analysisResult.reason instanceof Error
          ? analysisResult.reason.message
          : "Could not load analysis details.",
      );
    }

    if (explanationResult.status === "fulfilled") {
      setAnalysisExplanation(explanationResult.value.explanation);
    } else {
      setAnalysisExplanationError(
        explanationResult.reason instanceof Error
          ? explanationResult.reason.message
          : "Could not load the AI summary.",
      );
    }

    setIsLoadingAnalysisDetail(false);
  }

  function clearSessionState(nextLoginError: string | null) {
    setAuthToken(null);
    setOperator(null);
    setScenarios([]);
    setSelectedScenarioId(null);
    setInvestigation(null);
    setAuditEvents([]);
    setCases([]);
    setSelectedCaseId(null);
    setActiveCaseDetail(null);
    setIsLoadingCaseDetail(false);
    setCaseDetailError(null);
    setIsSubmittingCaseComment(false);
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

  // -----------------------------------------------------------------------
  // Public actions
  // -----------------------------------------------------------------------

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

  function handleLogout() {
    window.localStorage.removeItem(tokenStorageKey);
    clearSessionState(null);
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

  async function handleCreateCase() {
    if (!authToken || !activeInvestigation) return;
    try {
      const result = await createCaseFromInvestigation(
        authToken,
        activeInvestigation.scenario.scenario_id,
      );
      await refreshWorkspaceSlices(authToken, {
        alerts: true,
        audit: true,
        cases: true,
        stats: true,
      });
      setActiveView("cases");
      await loadCaseDetail(authToken, result.case.case_id);
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
      // Inline analyst action
    }
  }

  async function handleCaseSelection(caseId: string) {
    if (!authToken) return;
    setActiveView("cases");
    if (activeCaseDetail?.case.case_id === caseId) {
      setSelectedCaseId(caseId);
      return;
    }
    await loadCaseDetail(authToken, caseId);
  }

  async function handleAddCaseComment(caseId: string, body: string) {
    if (!authToken) return;
    const trimmedBody = body.trim();
    if (!trimmedBody) return;

    setIsSubmittingCaseComment(true);
    setCaseDetailError(null);
    setErrorMessage(null);

    try {
      await addCaseComment(authToken, caseId, trimmedBody);
      await refreshWorkspaceSlices(authToken, { audit: true, cases: true, stats: true });
      await loadCaseDetail(authToken, caseId);
    } catch (error) {
      setCaseDetailError(
        error instanceof Error ? error.message : "Could not add a comment to this case.",
      );
      throw error;
    } finally {
      setIsSubmittingCaseComment(false);
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
      if (selectedCaseId === caseId || activeCaseDetail?.case.case_id === caseId) {
        await loadCaseDetail(authToken, caseId);
      }
    } catch {
      // Inline analyst action
    }
  }

  async function handleCreateCaseFromAlert(alertId: string) {
    if (!authToken) return;
    try {
      const result = await createCaseFromAlert(authToken, alertId);
      await refreshWorkspaceSlices(authToken, {
        alerts: true,
        audit: true,
        cases: true,
        stats: true,
      });
      setActiveView("cases");
      await loadCaseDetail(authToken, result.case.case_id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create case.");
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
    try {
      const result = await createCaseFromAnalysis(authToken, activeAnalysis.dataset_id);
      await refreshWorkspaceSlices(authToken, {
        alerts: true,
        audit: true,
        cases: true,
        stats: true,
      });
      setActiveView("cases");
      await loadCaseDetail(authToken, result.case.case_id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create case.");
    }
  }

  // -----------------------------------------------------------------------
  // Return
  // -----------------------------------------------------------------------

  const state: DashboardState = {
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
    investigation,
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
  };

  const actions: DashboardActions = {
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
  };

  return [state, actions];
}
