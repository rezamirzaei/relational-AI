import { Dashboard } from "@/components/dashboard";
import { fetchInvestigationServer, fetchScenarioCatalog } from "@/lib/api";
import type { InvestigationResponse, ScenarioOverview } from "@/lib/contracts";

export const dynamic = "force-dynamic";

type BootstrapData = {
  bootstrapError: string | null;
  initialInvestigation: InvestigationResponse | null;
  scenarios: ScenarioOverview[];
};

async function getBootstrapData(): Promise<BootstrapData> {
  try {
    const scenarioCatalog = await fetchScenarioCatalog();
    const firstScenarioId = scenarioCatalog.scenarios[0]?.scenario_id;
    const initialInvestigation = firstScenarioId
      ? await fetchInvestigationServer(firstScenarioId)
      : null;

    return {
      bootstrapError: null,
      initialInvestigation,
      scenarios: scenarioCatalog.scenarios,
    };
  } catch (error) {
    return {
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
      bootstrapError={bootstrapData.bootstrapError}
      initialInvestigation={bootstrapData.initialInvestigation}
      initialScenarios={bootstrapData.scenarios}
    />
  );
}
