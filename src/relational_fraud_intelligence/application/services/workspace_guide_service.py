from relational_fraud_intelligence.domain.models import OperatorRole, RoleStory, WorkspaceGuide


class WorkspaceGuideService:
    def get_guide(self) -> WorkspaceGuide:
        return WorkspaceGuide(
            primary_workflow_title="Primary Workflow: Upload -> Analyze -> Alert -> Case",
            primary_workflow_summary=(
                "The main product path starts with transaction data. Analysts upload a "
                "dataset, run deterministic analysis, review the generated alerts, and "
                "open a case when the findings warrant investigation."
            ),
            role_stories=[
                RoleStory(
                    story_id="frontline-analyst",
                    persona_name="Nadia",
                    title="Frontline Fraud Analyst",
                    platform_role=OperatorRole.ANALYST,
                    goal="Turn suspicious uploaded data into a triaged case quickly.",
                    workflow_steps=[
                        "Upload a transaction export from a bank, fintech, or merchant feed.",
                        "Run deterministic analysis and inspect the strongest anomaly flags.",
                        "Review the generated alerts and open a case with a clear summary.",
                    ],
                    success_signal="A high-risk dataset becomes an alert-backed case in one pass.",
                    recommended_view="analyze",
                ),
                RoleStory(
                    story_id="queue-owner",
                    persona_name="Marcus",
                    title="Queue Owner Analyst",
                    platform_role=OperatorRole.ANALYST,
                    goal="Keep the alert queue moving without losing the deterministic evidence.",
                    workflow_steps=[
                        "Review newly generated alerts from recent analyses.",
                        "Prioritize open cases by risk and triage status.",
                        "Resolve false positives or escalate confirmed fraud findings.",
                    ],
                    success_signal=(
                        "New alerts do not sit unacknowledged and high-risk cases move forward."
                    ),
                    recommended_view="alerts",
                ),
                RoleStory(
                    story_id="platform-admin",
                    persona_name="Priya",
                    title="Platform Administrator",
                    platform_role=OperatorRole.ADMIN,
                    goal="Verify that the workflow is healthy, auditable, and usable by operators.",
                    workflow_steps=[
                        "Check workflow throughput and queue pressure from the dashboard.",
                        "Inspect audit activity for critical operator actions.",
                        "Confirm that bootstrap operators, database health, and "
                        "rate limiting remain stable.",
                    ],
                    success_signal="The platform stays trustworthy while analysts work the queue.",
                    recommended_view="overview",
                ),
            ],
            scoring_guarantees=[
                "Risk scores are computed from deterministic Benford, outlier, "
                "velocity, and round-amount analyzers.",
                "Alert generation thresholds are deterministic and do not depend "
                "on the LLM explanation layer.",
                "Cases remain linked to datasets or reference scenarios with "
                "persistent audit history.",
            ],
            llm_positioning_note=(
                "The copilot layer explains deterministic results. It does not change risk scores, "
                "suppress alerts, or open cases on its own."
            ),
        )
