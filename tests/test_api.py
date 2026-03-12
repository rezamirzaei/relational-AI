from fastapi.testclient import TestClient

from relational_fraud_intelligence.app import create_app


def test_list_scenarios_returns_seed_data() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/scenarios")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["scenarios"]) == 3


def test_health_reports_database_ready() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database_status"] == "ready"


def test_investigate_scenario_returns_case_payload() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/investigations",
            json={"scenario_id": "travel-ato-escalation"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["investigation"]["scenario"]["scenario_id"] == "travel-ato-escalation"
    assert payload["investigation"]["provider_summary"]["active_text_provider"] == "keyword"
