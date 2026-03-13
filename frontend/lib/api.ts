import type {
  AnalysisResponse,
  AnalysisExplanationResponse,
  AuditEventsResponse,
  CreateCaseFromAnalysisResponse,
  CreateCaseFromAlertResponse,
  CreateCaseFromInvestigationResponse,
  CreateCaseResponse,
  CurrentOperatorResponse,
  DashboardStatsResponse,
  DatasetInfo,
  DatasetListResponse,
  GetCaseResponse,
  HealthResponse,
  InvestigationResponse,
  ListAlertsResponse,
  ListCasesResponse,
  LoginResponse,
  ScenarioCatalogResponse,
  WorkspaceGuideResponse,
} from "@/lib/contracts";

const browserApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001/api/v1";
const serverApiBaseUrl = process.env.API_BASE_URL ?? browserApiBaseUrl;

async function fetchJson<T>(
  url: string,
  init?: RequestInit,
  token?: string,
): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the default message when the backend returns no JSON error body.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function fetchHealthServer(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>(`${serverApiBaseUrl}/health`);
}

export async function fetchWorkspaceGuideServer(): Promise<WorkspaceGuideResponse> {
  return fetchJson<WorkspaceGuideResponse>(`${serverApiBaseUrl}/workspace/guide`);
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

export async function loginOperator(
  username: string,
  password: string,
): Promise<LoginResponse> {
  return fetchJson<LoginResponse>(`${browserApiBaseUrl}/auth/token`, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function fetchCurrentOperator(
  token: string,
): Promise<CurrentOperatorResponse> {
  return fetchJson<CurrentOperatorResponse>(`${browserApiBaseUrl}/auth/me`, undefined, token);
}

// ---------------------------------------------------------------------------
// Scenarios & Investigations
// ---------------------------------------------------------------------------

export async function fetchScenarioCatalog(
  token: string,
): Promise<ScenarioCatalogResponse> {
  return fetchJson<ScenarioCatalogResponse>(`${browserApiBaseUrl}/scenarios`, undefined, token);
}

export async function fetchInvestigationClient(
  token: string,
  scenarioId: string,
): Promise<InvestigationResponse> {
  return fetchJson<InvestigationResponse>(
    `${browserApiBaseUrl}/investigations`,
    {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId }),
    },
    token,
  );
}

export async function createCaseFromInvestigation(
  token: string,
  scenarioId: string,
): Promise<CreateCaseFromInvestigationResponse> {
  return fetchJson<CreateCaseFromInvestigationResponse>(
    `${browserApiBaseUrl}/investigations/${scenarioId}/case`,
    { method: "POST" },
    token,
  );
}

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

export async function createCase(
  token: string,
  params: {
    source_type?: "scenario" | "dataset";
    source_id?: string;
    scenario_id?: string;
    title: string;
    summary: string;
    priority?: string;
    risk_score?: number;
    risk_level?: string;
  },
): Promise<CreateCaseResponse> {
  return fetchJson<CreateCaseResponse>(
    `${browserApiBaseUrl}/cases`,
    { method: "POST", body: JSON.stringify(params) },
    token,
  );
}

export async function createCaseFromAnalysis(
  token: string,
  datasetId: string,
): Promise<CreateCaseFromAnalysisResponse> {
  return fetchJson<CreateCaseFromAnalysisResponse>(
    `${browserApiBaseUrl}/datasets/${datasetId}/case`,
    { method: "POST" },
    token,
  );
}

export async function fetchCases(
  token: string,
  params?: { status?: string; page?: number },
): Promise<ListCasesResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.page) query.set("page", String(params.page));
  const qs = query.toString();
  return fetchJson<ListCasesResponse>(
    `${browserApiBaseUrl}/cases${qs ? `?${qs}` : ""}`,
    undefined,
    token,
  );
}

export async function fetchCase(token: string, caseId: string): Promise<GetCaseResponse> {
  return fetchJson<GetCaseResponse>(`${browserApiBaseUrl}/cases/${caseId}`, undefined, token);
}

export async function updateCaseStatus(
  token: string,
  caseId: string,
  params: { status: string; disposition?: string; resolution_notes?: string },
): Promise<unknown> {
  return fetchJson(`${browserApiBaseUrl}/cases/${caseId}/status`, {
    method: "PATCH",
    body: JSON.stringify(params),
  }, token);
}

export async function addCaseComment(
  token: string,
  caseId: string,
  body: string,
): Promise<unknown> {
  return fetchJson(`${browserApiBaseUrl}/cases/${caseId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  }, token);
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export async function fetchAlerts(
  token: string,
  params?: { status?: string; severity?: string; page?: number },
): Promise<ListAlertsResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.severity) query.set("severity", params.severity);
  if (params?.page) query.set("page", String(params.page));
  const qs = query.toString();
  return fetchJson<ListAlertsResponse>(
    `${browserApiBaseUrl}/alerts${qs ? `?${qs}` : ""}`,
    undefined,
    token,
  );
}

export async function updateAlertStatus(
  token: string,
  alertId: string,
  params: { status: string; linked_case_id?: string },
): Promise<unknown> {
  return fetchJson(`${browserApiBaseUrl}/alerts/${alertId}`, {
    method: "PATCH",
    body: JSON.stringify(params),
  }, token);
}

export async function createCaseFromAlert(
  token: string,
  alertId: string,
): Promise<CreateCaseFromAlertResponse> {
  return fetchJson<CreateCaseFromAlertResponse>(
    `${browserApiBaseUrl}/alerts/${alertId}/case`,
    { method: "POST" },
    token,
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function fetchDashboardStats(
  token: string,
): Promise<DashboardStatsResponse> {
  return fetchJson<DashboardStatsResponse>(
    `${browserApiBaseUrl}/dashboard/stats`,
    undefined,
    token,
  );
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export async function fetchAuditEvents(token: string): Promise<AuditEventsResponse> {
  return fetchJson<AuditEventsResponse>(
    `${browserApiBaseUrl}/audit-events?limit=20`,
    undefined,
    token,
  );
}

// ---------------------------------------------------------------------------
// Datasets & Analysis
// ---------------------------------------------------------------------------

export async function uploadDataset(token: string, file: File): Promise<DatasetInfo> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${browserApiBaseUrl}/datasets/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchDatasets(token: string): Promise<DatasetListResponse> {
  return fetchJson<DatasetListResponse>(
    `${browserApiBaseUrl}/datasets`,
    undefined,
    token,
  );
}

export async function analyzeDataset(token: string, datasetId: string): Promise<AnalysisResponse> {
  return fetchJson<AnalysisResponse>(
    `${browserApiBaseUrl}/datasets/${datasetId}/analyze`,
    { method: "POST" },
    token,
  );
}

export async function fetchAnalysisResult(
  token: string,
  datasetId: string,
): Promise<AnalysisResponse> {
  return fetchJson<AnalysisResponse>(
    `${browserApiBaseUrl}/datasets/${datasetId}/analysis`,
    undefined,
    token,
  );
}

export async function fetchAnalysisExplanation(
  token: string,
  datasetId: string,
  audience: "analyst" | "admin",
): Promise<AnalysisExplanationResponse> {
  return fetchJson<AnalysisExplanationResponse>(
    `${browserApiBaseUrl}/datasets/${datasetId}/explanation?audience=${audience}`,
    undefined,
    token,
  );
}
