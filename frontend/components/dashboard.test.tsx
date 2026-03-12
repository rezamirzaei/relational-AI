import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/components/dashboard";
import { fetchInvestigationClient } from "@/lib/api";
import type {
  HealthResponse,
  InvestigationResponse,
  ScenarioOverview,
} from "@/lib/contracts";

vi.mock("@/lib/api", () => ({
  fetchInvestigationClient: vi.fn(),
}));

const mockedFetchInvestigationClient = vi.mocked(fetchInvestigationClient);

const backendHealth: HealthResponse = {
  status: "ok",
  app_name: "Relational Fraud Intelligence",
  environment: "test",
  database_status: "ready",
  seeded_scenarios: 3,
};

const scenarios: ScenarioOverview[] = [
  {
    scenario_id: "synthetic-identity-ring",
    title: "Synthetic Identity Gift Card Ring",
    industry: "Fintech",
    summary: "Gift card liquidation on shared devices.",
    hypothesis: "Synthetic identities are cashing out through digital goods.",
    tags: ["fraud", "synthetic-identity", "device-ring"],
    transaction_count: 5,
    total_volume: 4789.99,
    baseline_risk: "critical",
  },
  {
    scenario_id: "travel-ato-escalation",
    title: "Travel Account Takeover Escalation",
    industry: "Digital Banking",
    summary: "Cross-border travel spend from a new device.",
    hypothesis: "A compromised account is being rapidly monetized.",
    tags: ["fraud", "account-takeover", "cross-border"],
    transaction_count: 3,
    total_volume: 6980,
    baseline_risk: "high",
  },
];

function buildInvestigationResponse(
  scenario: ScenarioOverview,
): InvestigationResponse {
  return {
    investigation: {
      scenario,
      risk_level: scenario.baseline_risk,
      total_risk_score: scenario.baseline_risk === "critical" ? 92 : 76,
      summary: `${scenario.title} requires immediate review.`,
      metrics: {
        total_transaction_volume: scenario.total_volume,
        suspicious_transaction_volume: scenario.total_volume - 250,
        suspicious_transaction_count: scenario.transaction_count - 1,
        shared_device_count: 1,
        linked_customer_count: 2,
      },
      provider_summary: {
        requested_reasoning_provider: "local-rule-engine",
        active_reasoning_provider: "local-rule-engine",
        requested_text_provider: "keyword",
        active_text_provider: "keyword",
        notes: ["Deterministic fraud heuristics are active."],
      },
      top_rule_hits: [
        {
          rule_code: "shared-device-cluster",
          title: "Shared device cluster",
          weight: 28,
          narrative: "Multiple identities authenticated from the same device.",
        },
      ],
      graph_links: [
        {
          relation: "shares-device",
          explanation: "Both identities used the same low-trust device.",
          source: {
            entity_type: "customer",
            entity_id: "cust-1",
            display_name: "Amina Rahman",
          },
          target: {
            entity_type: "customer",
            entity_id: "cust-2",
            display_name: "Noah Carter",
          },
        },
      ],
      text_signals: [
        {
          signal_id: "note::1::synthetic-identity",
          provider: "keyword",
          source_kind: "investigator-note",
          source_id: "note-1",
          label: "synthetic identity",
          confidence: 0.94,
          rationale: "The note references synthetic identity behavior.",
        },
      ],
      suspicious_transactions: [
        {
          transaction_id: "txn-1",
          customer_id: "cust-1",
          account_id: "acct-1",
          device_id: "dev-1",
          merchant_id: "merchant-1",
          occurred_at: "2026-03-11T09:17:00",
          amount: 980,
          currency: "USD",
          channel: "wallet",
          status: "review",
        },
      ],
      recommended_actions: [
        "Freeze outbound spend pending enhanced verification.",
      ],
    },
  };
}

describe("Dashboard", () => {
  beforeEach(() => {
    mockedFetchInvestigationClient.mockReset();
  });

  it("renders runtime posture and initial investigation details", () => {
    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        initialInvestigation={buildInvestigationResponse(scenarios[0])}
        initialScenarios={scenarios}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Relational Fraud Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("ready").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Synthetic Identity Gift Card Ring requires immediate review."),
    ).toBeInTheDocument();
  });

  it("filters scenarios from the search box", () => {
    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        initialInvestigation={buildInvestigationResponse(scenarios[0])}
        initialScenarios={scenarios}
      />,
    );

    fireEvent.change(screen.getByLabelText("Search scenarios"), {
      target: { value: "travel" },
    });

    const scenarioList = within(screen.getByTestId("scenario-list"));
    expect(
      scenarioList.queryByText("Synthetic Identity Gift Card Ring"),
    ).not.toBeInTheDocument();
    expect(
      scenarioList.getByText("Travel Account Takeover Escalation"),
    ).toBeInTheDocument();
  });

  it("loads a scenario when the operator selects it", async () => {
    mockedFetchInvestigationClient.mockResolvedValue(
      buildInvestigationResponse(scenarios[1]),
    );

    render(
      <Dashboard
        backendHealth={backendHealth}
        bootstrapError={null}
        initialInvestigation={buildInvestigationResponse(scenarios[0])}
        initialScenarios={scenarios}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /travel account takeover/i }));

    await waitFor(() => {
      expect(mockedFetchInvestigationClient).toHaveBeenCalledWith(
        "travel-ato-escalation",
      );
      expect(
        screen.getByText("Travel Account Takeover Escalation requires immediate review."),
      ).toBeInTheDocument();
    });
  });
});
