from fastapi.testclient import TestClient

from relational_fraud_intelligence.app import create_app


def test_health_reports_database_and_rate_limit_ready() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database_status"] == "ready"
    assert payload["rate_limit_status"] == "ready"


def test_protected_routes_require_authentication() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/scenarios")

    assert response.status_code == 401


def test_operator_can_authenticate_and_load_scenarios() -> None:
    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")

        response = client.get(
            "/api/v1/scenarios",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["scenarios"]) == 3


def test_investigate_scenario_returns_case_payload_for_authenticated_operator() -> None:
    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")
        response = client.post(
            "/api/v1/investigations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"scenario_id": "travel-ato-escalation"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["investigation"]["scenario"]["scenario_id"] == "travel-ato-escalation"
    assert payload["investigation"]["provider_summary"]["active_text_provider"] == "keyword"


def test_admin_can_list_audit_events() -> None:
    with TestClient(create_app()) as client:
        analyst_token = authenticate(
            client,
            username="analyst",
            password="AnalystPassword123!",
        )
        client.get(
            "/api/v1/scenarios",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )

        admin_token = authenticate(client, username="admin", password="AdminPassword123!")
        response = client.get(
            "/api/v1/audit-events?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert any(event["action"] == "list-scenarios" for event in payload["events"])
    assert any(event["actor_username"] == "analyst" for event in payload["events"])


def test_analyst_cannot_list_audit_events() -> None:
    with TestClient(create_app()) as client:
        analyst_token = authenticate(
            client,
            username="analyst",
            password="AnalystPassword123!",
        )
        response = client.get(
            "/api/v1/audit-events",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )

    assert response.status_code == 403


def authenticate(client: TestClient, *, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    return str(payload["access_token"])
