from pydantic import BaseModel

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)
from relational_fraud_intelligence.application.ports.reasoner import RiskReasoner
from relational_fraud_intelligence.settings import AppSettings


class RelationalAIProjection(BaseModel):
    projected_row_count: int
    projected_table_names: list[str]


class RelationalAIRiskReasoner:
    def __init__(self, settings: AppSettings, local_reasoner: RiskReasoner) -> None:
        self._settings = settings
        self._local_reasoner = local_reasoner

    def reason(self, command: ReasonAboutRiskCommand) -> ReasonAboutRiskResult:
        projection = self._project_scenario(command)
        base_result = self._local_reasoner.reason(command)
        return base_result.model_copy(
            update={
                "requested_provider": "relationalai",
                "active_provider": "hybrid-relationalai",
                "provider_notes": [
                    (
                        "Projected scenario data through RelationalAI semantics "
                        f"({projection.projected_row_count} rows across {', '.join(projection.projected_table_names)})."
                    ),
                    *base_result.provider_notes,
                ],
            }
        )

    def _project_scenario(self, command: ReasonAboutRiskCommand) -> RelationalAIProjection:
        from relationalai.config import Config, create_config
        from relationalai.semantics import Model

        if self._settings.relationalai_use_external_config:
            config = create_config()
        else:
            config = Config(
                connections={"local": {"type": "duckdb", "path": self._settings.relationalai_duckdb_path}},
                default_connection="local",
                install_mode=True,
            )

        model = Model(name="fraud-projection", config=config)
        transaction_rows = model.data(
            [
                {
                    "transaction_id": transaction.transaction_id,
                    "account_id": transaction.account_id,
                    "device_id": transaction.device_id,
                    "merchant_id": transaction.merchant_id,
                    "amount": transaction.amount,
                }
                for transaction in command.scenario.transactions
            ]
        )
        device_rows = model.data(
            [
                {
                    "device_id": device.device_id,
                    "linked_customer_count": len(device.linked_customer_ids),
                    "trust_score": device.trust_score,
                }
                for device in command.scenario.devices
            ]
        )

        transaction_frame = model.select(
            transaction_rows.transaction_id,
            transaction_rows.account_id,
            transaction_rows.amount,
        ).to_df()
        device_frame = model.select(
            device_rows.device_id,
            device_rows.linked_customer_count,
            device_rows.trust_score,
        ).to_df()

        return RelationalAIProjection(
            projected_row_count=len(transaction_frame) + len(device_frame),
            projected_table_names=["transactions", "devices"],
        )
