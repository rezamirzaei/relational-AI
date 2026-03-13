import { Dashboard } from "@/components/dashboard";
import { fetchHealthServer, fetchWorkspaceGuideServer } from "@/lib/api";
import type { HealthResponse, WorkspaceGuide } from "@/lib/contracts";

export const dynamic = "force-dynamic";

type BootstrapData = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
  workspaceGuide: WorkspaceGuide | null;
};

async function getBootstrapData(): Promise<BootstrapData> {
  const [healthResult, guideResult] = await Promise.allSettled([
    fetchHealthServer(),
    fetchWorkspaceGuideServer(),
  ]);

  return {
    backendHealth: healthResult.status === "fulfilled" ? healthResult.value : null,
    bootstrapError:
      healthResult.status === "rejected"
        ? healthResult.reason instanceof Error
          ? healthResult.reason.message
          : "The backend is not reachable yet."
        : null,
    workspaceGuide: guideResult.status === "fulfilled" ? guideResult.value.guide : null,
  };
}

export default async function HomePage() {
  const bootstrapData = await getBootstrapData();

  return (
    <Dashboard
      backendHealth={bootstrapData.backendHealth}
      bootstrapError={bootstrapData.bootstrapError}
      workspaceGuide={bootstrapData.workspaceGuide}
    />
  );
}
