import type {
  AuditEventsResponse,
  CreateCaseResponse,
  CurrentOperatorResponse,
  DashboardStatsResponse,
  GetCaseResponse,
  HealthResponse,
  InvestigationResponse,
  ListAlertsResponse,
  ListCasesResponse,
  LoginResponse,
  ScenarioCatalogResponse,
} from "@/lib/contracts";

const browserApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
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

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

export async function createCase(
  token: string,
  params: { scenario_id: string; title: string; summary: string; priority?: string },
): Promise<CreateCaseResponse> {
  return fetchJson<CreateCaseResponse>(
    `${browserApiBaseUrl}/cases`,
    { method: "POST", body: JSON.stringify(params) },
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
