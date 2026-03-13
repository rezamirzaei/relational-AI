from pathlib import Path

import pytest
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
    monkeypatch: pytest.MonkeyPatch,
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
    assert payload["investigation"]["investigation_leads"]


def test_scenario_investigation_can_create_a_linked_case() -> None:
    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")

        investigate_response = client.post(
            "/api/v1/investigations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"scenario_id": "synthetic-identity-ring"},
        )
        assert investigate_response.status_code == 200

        create_case_response = client.post(
            "/api/v1/investigations/synthetic-identity-ring/case",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert create_case_response.status_code == 200
    payload = create_case_response.json()
    assert payload["investigation"]["scenario"]["scenario_id"] == "synthetic-identity-ring"
    assert payload["investigation"]["investigation_leads"]
    assert payload["case"]["source_type"] == "scenario"
    assert payload["case"]["source_id"] == "synthetic-identity-ring"
    assert "Primary lead:" in payload["case"]["summary"]
    assert payload["linked_alerts"]
    assert all(
        alert["linked_case_id"] == payload["case"]["case_id"] for alert in payload["linked_alerts"]
    )


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


def test_dataset_analysis_generates_alerts_and_a_linked_case_from_analysis() -> None:
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
            f"/api/v1/datasets/{dataset_id}/case",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert create_case_response.status_code == 200
        create_case_payload = create_case_response.json()
        created_case = create_case_payload["case"]
        assert created_case["source_type"] == "dataset"
        assert created_case["source_id"] == dataset_id
        assert created_case["risk_score"] == analysis["risk_score"]
        assert "Primary lead:" in created_case["summary"]
        assert create_case_payload["linked_alerts"]
        assert all(
            alert["linked_case_id"] == created_case["case_id"]
            for alert in create_case_payload["linked_alerts"]
        )

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


def test_dataset_case_detail_exposes_transactions_alerts_and_comments() -> None:
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

        create_case_response = client.post(
            f"/api/v1/datasets/{dataset_id}/case",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert create_case_response.status_code == 200
        case_id = create_case_response.json()["case"]["case_id"]

        comment_response = client.post(
            f"/api/v1/cases/{case_id}/comments",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "body": (
                    "Reviewed the linked transactions and the merchant concentration "
                    "is abnormal."
                )
            },
        )
        assert comment_response.status_code == 200

        detail_response = client.get(
            f"/api/v1/cases/{case_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["case"]["case_id"] == case_id
    assert payload["dataset"]["dataset_id"] == dataset_id
    assert payload["analysis"]["dataset_id"] == dataset_id
    assert payload["related_alerts"]
    assert any(alert["linked_case_id"] == case_id for alert in payload["related_alerts"])
    assert len(payload["dataset_transactions"]) == payload["dataset"]["row_count"]
    assert payload["dataset_transactions"][0]["transaction_id"]
    assert payload["comments"][0]["body"].startswith("Reviewed the linked transactions")


def test_scenario_case_detail_exposes_transactions_notes_and_comments() -> None:
    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")

        create_case_response = client.post(
            "/api/v1/investigations/synthetic-identity-ring/case",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert create_case_response.status_code == 200
        case_id = create_case_response.json()["case"]["case_id"]

        comment_response = client.post(
            f"/api/v1/cases/{case_id}/comments",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"body": "Device overlap and note history justify escalation."},
        )
        assert comment_response.status_code == 200

        detail_response = client.get(
            f"/api/v1/cases/{case_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["case"]["case_id"] == case_id
    assert payload["investigation"]["scenario"]["scenario_id"] == "synthetic-identity-ring"
    assert payload["investigation"]["investigation_leads"]
    assert payload["scenario_transactions"]
    assert payload["investigator_notes"]
    assert payload["related_alerts"]
    assert payload["comments"][0]["body"] == "Device overlap and note history justify escalation."


def test_case_status_update_uses_path_case_id() -> None:
    with TestClient(create_app()) as client:
        access_token = authenticate(client, username="analyst", password="AnalystPassword123!")

        create_case_response = client.post(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "scenario_id": "travel-ato-escalation",
                "title": "Travel escalation review",
                "summary": "Review suspicious travel activity before customer contact.",
            },
        )
        assert create_case_response.status_code == 200
        case_id = create_case_response.json()["case"]["case_id"]

        update_response = client.patch(
            f"/api/v1/cases/{case_id}/status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "status": "resolved",
                "disposition": "confirmed-fraud",
                "resolution_notes": "Resolved from the queue without requiring a body case_id.",
            },
        )

    assert update_response.status_code == 200
    payload = update_response.json()["case"]
    assert payload["case_id"] == case_id
    assert payload["status"] == "resolved"
    assert payload["disposition"] == "confirmed-fraud"
    assert (
        payload["resolution_notes"] == "Resolved from the queue without requiring a body case_id."
    )
    assert payload["resolved_at"] is not None


def test_alert_status_update_uses_path_alert_id() -> None:
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

        alerts_response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert alerts_response.status_code == 200
        alert = next(
            item
            for item in alerts_response.json()["alerts"]
            if item["source_type"] == "dataset" and item["source_id"] == dataset_id
        )

        update_response = client.patch(
            f"/api/v1/alerts/{alert['alert_id']}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"status": "acknowledged"},
        )

    assert update_response.status_code == 200
    payload = update_response.json()["alert"]
    assert payload["alert_id"] == alert["alert_id"]
    assert payload["status"] == "acknowledged"
    assert payload["acknowledged_at"] is not None


def test_alert_case_creation_links_the_alert_and_rejects_duplicates() -> None:
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

        alerts_response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert alerts_response.status_code == 200
        alert = next(
            item
            for item in alerts_response.json()["alerts"]
            if item["source_type"] == "dataset" and item["source_id"] == dataset_id
        )

        create_case_response = client.post(
            f"/api/v1/alerts/{alert['alert_id']}/case",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert create_case_response.status_code == 200
        payload = create_case_response.json()
        assert payload["case"]["source_type"] == "dataset"
        assert payload["case"]["source_id"] == dataset_id
        assert payload["case"]["title"] == f"Alert review: {alert['title']}"
        assert payload["alert"]["status"] == "investigating"
        assert payload["alert"]["linked_case_id"] == payload["case"]["case_id"]

        list_cases_response = client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_cases_response.status_code == 200
        assert any(
            case["case_id"] == payload["case"]["case_id"]
            for case in list_cases_response.json()["cases"]
        )

        list_alerts_response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_alerts_response.status_code == 200
        linked_alert = next(
            item
            for item in list_alerts_response.json()["alerts"]
            if item["alert_id"] == alert["alert_id"]
        )
        assert linked_alert["linked_case_id"] == payload["case"]["case_id"]

        duplicate_response = client.post(
            f"/api/v1/alerts/{alert['alert_id']}/case",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert duplicate_response.status_code == 409
        assert payload["case"]["case_id"] in duplicate_response.json()["detail"]


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
    assert payload["provider_summary"]["source_of_truth"] == "statistical-and-behavioral-analysis"
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
