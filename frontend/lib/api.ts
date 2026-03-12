import type {
  HealthResponse,
  InvestigationResponse,
  ScenarioCatalogResponse,
} from "@/lib/contracts";

const browserApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const serverApiBaseUrl = process.env.API_BASE_URL ?? browserApiBaseUrl;

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
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

export async function fetchScenarioCatalog(): Promise<ScenarioCatalogResponse> {
  return fetchJson<ScenarioCatalogResponse>(`${serverApiBaseUrl}/scenarios`);
}

export async function fetchInvestigationServer(
  scenarioId: string,
): Promise<InvestigationResponse> {
  return fetchJson<InvestigationResponse>(`${serverApiBaseUrl}/investigations`, {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
}

export async function fetchInvestigationClient(
  scenarioId: string,
): Promise<InvestigationResponse> {
  return fetchJson<InvestigationResponse>(`${browserApiBaseUrl}/investigations`, {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
}
