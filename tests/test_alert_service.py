"""Tests for the alert service and auto-generation pipeline."""

from __future__ import annotations

import pytest

from relational_fraud_intelligence.application.dto.alerts import (
    CreateAlertCommand,
    GetAlertQuery,
    ListAlertsQuery,
    UpdateAlertStatusCommand,
)
from relational_fraud_intelligence.application.services.alert_service import AlertService
from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    RiskLevel,
    WorkflowSourceType,
)
from relational_fraud_intelligence.infrastructure.repositories.memory import InMemoryAlertRepository


@pytest.fixture()
def alert_service() -> AlertService:
    return AlertService(InMemoryAlertRepository())


async def test_create_alert_returns_new_alert(alert_service: AlertService) -> None:
    result = await alert_service.create_alert(
        CreateAlertCommand(
            scenario_id="test-scenario",
            rule_code="shared-device-cluster",
            title="Shared device cluster detected",
            severity=RiskLevel.HIGH,
            narrative="Multiple customers authenticated from the same low-trust device.",
        )
    )

    assert result.alert.status == AlertStatus.NEW
    assert result.alert.severity == RiskLevel.HIGH
    assert result.alert.rule_code == "shared-device-cluster"
    assert result.alert.source_type == WorkflowSourceType.SCENARIO


async def test_acknowledge_alert_sets_acknowledged_timestamp(alert_service: AlertService) -> None:
    created = await alert_service.create_alert(
        CreateAlertCommand(
            scenario_id="s1",
            rule_code="rapid-spend-burst",
            title="Rapid spend burst",
            severity=RiskLevel.CRITICAL,
            narrative="High-value transactions in tight window.",
        )
    )

    result = await alert_service.update_status(
        UpdateAlertStatusCommand(
            alert_id=created.alert.alert_id,
            status=AlertStatus.ACKNOWLEDGED,
        )
    )

    assert result.alert.status == AlertStatus.ACKNOWLEDGED
    assert result.alert.acknowledged_at is not None


async def test_resolve_alert_as_false_positive(alert_service: AlertService) -> None:
    created = await alert_service.create_alert(
        CreateAlertCommand(
            scenario_id="s1",
            rule_code="cross-border-mismatch",
            title="Cross-border mismatch",
            severity=RiskLevel.MEDIUM,
            narrative="Merchant geography differs.",
        )
    )

    result = await alert_service.update_status(
        UpdateAlertStatusCommand(
            alert_id=created.alert.alert_id,
            status=AlertStatus.FALSE_POSITIVE,
        )
    )

    assert result.alert.status == AlertStatus.FALSE_POSITIVE
    assert result.alert.resolved_at is not None


async def test_reopening_alert_clears_terminal_timestamp(alert_service: AlertService) -> None:
    created = await alert_service.create_alert(
        CreateAlertCommand(
            scenario_id="s1",
            rule_code="cross-border-mismatch",
            title="Cross-border mismatch",
            severity=RiskLevel.MEDIUM,
            narrative="Merchant geography differs.",
        )
    )

    await alert_service.update_status(
        UpdateAlertStatusCommand(
            alert_id=created.alert.alert_id,
            status=AlertStatus.FALSE_POSITIVE,
        )
    )
    reopened = await alert_service.update_status(
        UpdateAlertStatusCommand(
            alert_id=created.alert.alert_id,
            status=AlertStatus.INVESTIGATING,
        )
    )

    assert reopened.alert.status == AlertStatus.INVESTIGATING
    assert reopened.alert.resolved_at is None


async def test_list_alerts_filters_by_severity(alert_service: AlertService) -> None:
    await alert_service.create_alert(
        CreateAlertCommand(
            scenario_id="s1",
            rule_code="r1",
            title="Low alert",
            severity=RiskLevel.LOW,
            narrative="Low risk.",
        )
    )
    await alert_service.create_alert(
        CreateAlertCommand(
            scenario_id="s2",
            rule_code="r2",
            title="Critical alert",
            severity=RiskLevel.CRITICAL,
            narrative="Critical risk.",
        )
    )

    result = await alert_service.list_alerts(ListAlertsQuery(severity=RiskLevel.CRITICAL))
    assert result.total_count == 1
    assert result.alerts[0].severity == RiskLevel.CRITICAL


async def test_auto_generate_alerts_from_high_risk_investigation(alert_service: AlertService) -> None:
    rule_hits = [
        {
            "rule_code": "shared-device-cluster",
            "title": "Shared device cluster",
            "narrative": "Test",
        },
        {"rule_code": "rapid-spend-burst", "title": "Rapid spend burst", "narrative": "Test"},
    ]

    generated = await alert_service.generate_alerts_from_investigation(
        scenario_id="test-scenario",
        risk_score=85,
        rule_hits=rule_hits,
    )

    assert len(generated) == 2
    assert all(a.severity == RiskLevel.CRITICAL for a in generated)
    assert all(a.status == AlertStatus.NEW for a in generated)


async def test_auto_generate_no_alerts_for_low_risk(alert_service: AlertService) -> None:
    generated = await alert_service.generate_alerts_from_investigation(
        scenario_id="test-scenario",
        risk_score=20,
        rule_hits=[{"rule_code": "r1", "title": "t1", "narrative": "n1"}],
    )

    assert len(generated) == 0


async def test_auto_generate_alerts_is_idempotent_per_source(alert_service: AlertService) -> None:
    rule_hits = [
        {
            "rule_code": "shared-device-cluster",
            "title": "Shared device cluster",
            "narrative": "Test",
        },
    ]

    first = await alert_service.generate_alerts_from_investigation(
        scenario_id="test-scenario",
        risk_score=85,
        rule_hits=rule_hits,
    )
    second = await alert_service.generate_alerts_from_investigation(
        scenario_id="test-scenario",
        risk_score=85,
        rule_hits=rule_hits,
    )

    assert len(first) == 1
    assert len(second) == 1
    assert second[0].alert_id == first[0].alert_id


async def test_get_nonexistent_alert_raises_lookup_error(alert_service: AlertService) -> None:
    with pytest.raises(LookupError):
        await alert_service.get_alert(GetAlertQuery(alert_id="does-not-exist"))


async def test_auto_generate_alerts_from_dataset_analysis(alert_service: AlertService) -> None:
    findings = [
        {
            "rule_code": "velocity-spike",
            "title": "Velocity spike detected",
            "narrative": "Account activity spiked above the baseline window.",
        }
    ]

    generated = await alert_service.generate_alerts_from_analysis(
        dataset_id="dataset-1",
        risk_score=62,
        findings=findings,
    )

    assert len(generated) == 1
    assert generated[0].source_type == WorkflowSourceType.DATASET
    assert generated[0].source_id == "dataset-1"
    assert generated[0].scenario_id is None
