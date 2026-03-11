import type { InvestigationResponse, ScenarioCatalogResponse } from "@/lib/contracts";

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
    throw new Error(`Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
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
