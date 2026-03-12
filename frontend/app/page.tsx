import { Dashboard } from "@/components/dashboard";
import {
  fetchHealthServer,
  fetchInvestigationServer,
  fetchScenarioCatalog,
} from "@/lib/api";
import type {
  HealthResponse,
  InvestigationResponse,
  ScenarioOverview,
} from "@/lib/contracts";

export const dynamic = "force-dynamic";

type BootstrapData = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
  initialInvestigation: InvestigationResponse | null;
  scenarios: ScenarioOverview[];
};

async function getBootstrapData(): Promise<BootstrapData> {
  try {
    const [backendHealth, scenarioCatalog] = await Promise.all([
      fetchHealthServer(),
      fetchScenarioCatalog(),
    ]);
    const firstScenarioId = scenarioCatalog.scenarios[0]?.scenario_id;
    const initialInvestigation = firstScenarioId
      ? await fetchInvestigationServer(firstScenarioId)
      : null;

    return {
      backendHealth,
      bootstrapError: null,
      initialInvestigation,
      scenarios: scenarioCatalog.scenarios,
    };
  } catch (error) {
    return {
      backendHealth: null,
      bootstrapError:
        error instanceof Error ? error.message : "The backend is not reachable yet.",
      initialInvestigation: null,
      scenarios: [],
    };
  }
}

export default async function HomePage() {
  const bootstrapData = await getBootstrapData();

  return (
    <Dashboard
      backendHealth={bootstrapData.backendHealth}
      bootstrapError={bootstrapData.bootstrapError}
      initialInvestigation={bootstrapData.initialInvestigation}
      initialScenarios={bootstrapData.scenarios}
    />
  );
}
