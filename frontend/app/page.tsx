import { Dashboard } from "@/components/dashboard";
import { fetchHealthServer } from "@/lib/api";
import type { HealthResponse } from "@/lib/contracts";

export const dynamic = "force-dynamic";

type BootstrapData = {
  backendHealth: HealthResponse | null;
  bootstrapError: string | null;
};

async function getBootstrapData(): Promise<BootstrapData> {
  try {
    const backendHealth = await fetchHealthServer();

    return {
      backendHealth,
      bootstrapError: null,
    };
  } catch (error) {
    return {
      backendHealth: null,
      bootstrapError:
        error instanceof Error ? error.message : "The backend is not reachable yet.",
    };
  }
}

export default async function HomePage() {
  const bootstrapData = await getBootstrapData();

  return (
    <Dashboard
      backendHealth={bootstrapData.backendHealth}
      bootstrapError={bootstrapData.bootstrapError}
    />
  );
}
