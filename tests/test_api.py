from pathlib import Path

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
    assert payload["provider_status"] == "ready"
    assert payload["provider_posture"]["active_text_signal_provider"] == "keyword"
    assert payload["provider_posture"]["active_explanation_provider"] == "deterministic"


def test_health_reports_provider_fallback_when_huggingface_is_requested_without_token(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RFI_TEXT_SIGNAL_PROVIDER", "huggingface")
    monkeypatch.setenv("RFI_EXPLANATION_PROVIDER", "huggingface")
    monkeypatch.delenv("RFI_HUGGINGFACE_API_TOKEN", raising=False)

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["provider_status"] == "degraded"
    assert payload["provider_posture"]["active_text_signal_provider"] == "keyword"
    assert payload["provider_posture"]["active_explanation_provider"] == "deterministic"
    assert payload["provider_posture"]["notes"]


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


def test_workspace_guide_exposes_primary_workflow_and_roles() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/workspace/guide")

    assert response.status_code == 200
    payload = response.json()["guide"]
    assert (
        payload["primary_workflow_title"] == "Primary Workflow: Upload -> Analyze -> Alert -> Case"
    )
    assert payload["role_stories"][0]["recommended_view"] == "analyze"
    assert payload["role_stories"][2]["platform_role"] == "admin"
    assert "does not change risk scores" in payload["llm_positioning_note"]


def test_dataset_analysis_generates_persistent_alerts_and_cases() -> None:
    sample_path = (
        Path(__file__).resolve().parent.parent / "docs" / "sample_data" / "sample_transactions.csv"
    )

    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")
        with sample_path.open("rb") as handle:
            upload_response = client.post(
                "/api/v1/datasets/upload",
                headers={"Authorization": f"Bearer {access_token}"},
                files={"file": ("sample_transactions.csv", handle, "text/csv")},
            )

        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["dataset_id"]

        analyze_response = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()["analysis"]
        assert analysis["dataset_id"] == dataset_id
        assert analysis["risk_score"] >= 35

        alerts_response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()["alerts"]
        assert any(
            alert["source_type"] == "dataset" and alert["source_id"] == dataset_id
            for alert in alerts
        )

        create_case_response = client.post(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "source_type": "dataset",
                "source_id": dataset_id,
                "title": "Dataset case",
                "summary": analysis["summary"],
                "priority": analysis["risk_level"],
                "risk_score": analysis["risk_score"],
                "risk_level": analysis["risk_level"],
            },
        )
        assert create_case_response.status_code == 200
        created_case = create_case_response.json()["case"]
        assert created_case["source_type"] == "dataset"
        assert created_case["source_id"] == dataset_id
        assert created_case["risk_score"] == analysis["risk_score"]

        list_cases_response = client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_cases_response.status_code == 200
        assert any(case["source_id"] == dataset_id for case in list_cases_response.json()["cases"])

        dashboard_response = client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert dashboard_response.status_code == 200
        stats = dashboard_response.json()["stats"]
        assert stats["total_datasets"] == 1
        assert stats["total_alerts"] >= 1
        assert stats["total_cases"] == 1


def test_dataset_explanation_returns_deterministic_operator_brief() -> None:
    sample_path = (
        Path(__file__).resolve().parent.parent / "docs" / "sample_data" / "sample_transactions.csv"
    )

    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")
        with sample_path.open("rb") as handle:
            upload_response = client.post(
                "/api/v1/datasets/upload",
                headers={"Authorization": f"Bearer {access_token}"},
                files={"file": ("sample_transactions.csv", handle, "text/csv")},
            )

        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["dataset_id"]

        analyze_response = client.post(
            f"/api/v1/datasets/{dataset_id}/analyze",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert analyze_response.status_code == 200

        explanation_response = client.get(
            f"/api/v1/datasets/{dataset_id}/explanation?audience=analyst",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert explanation_response.status_code == 200
    payload = explanation_response.json()["explanation"]
    assert payload["dataset_id"] == dataset_id
    assert payload["provider_summary"]["requested_provider"] == "deterministic"
    assert payload["provider_summary"]["source_of_truth"] == "deterministic-statistical-analysis"
    assert payload["recommended_actions"]
    assert any("source of truth" in item.lower() for item in payload["watchouts"])


def authenticate(client: TestClient, *, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    return str(payload["access_token"])
