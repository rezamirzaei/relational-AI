import type {
  AuditEventsResponse,
  CurrentOperatorResponse,
  HealthResponse,
  InvestigationResponse,
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

export async function fetchHealthServer(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>(`${serverApiBaseUrl}/health`);
}

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

export async function fetchAuditEvents(token: string): Promise<AuditEventsResponse> {
  return fetchJson<AuditEventsResponse>(
    `${browserApiBaseUrl}/audit-events?limit=20`,
    undefined,
    token,
  );
}
