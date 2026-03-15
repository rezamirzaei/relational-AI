"""Locust load-testing suite for the Relational Fraud Intelligence API.

Usage:
    # Start the API server first, then:
    locust -f tests/loadtest/locustfile.py

    # Headless run (CI-friendly):
    locust -f tests/loadtest/locustfile.py --headless \
        -u 50 -r 5 --run-time 60s \
        --host http://localhost:8001

Environment variables:
    RFI_LOAD_USERNAME  — login username  (default: analyst)
    RFI_LOAD_PASSWORD  — login password  (default: AnalystPassword123!)
"""

from __future__ import annotations  # noqa: I001

import os

from locust import HttpUser, between, task


API_PREFIX = "/api/v1"
DEFAULT_USERNAME = os.getenv("RFI_LOAD_USERNAME", "analyst")
DEFAULT_PASSWORD = os.getenv("RFI_LOAD_PASSWORD", "AnalystPassword123!")


class FraudAnalystUser(HttpUser):
    """Simulates an authenticated fraud analyst using the platform.

    The user logs in once during ``on_start`` and reuses the JWT token
    for all subsequent requests.  Task weights approximate real-world
    usage patterns: dashboard is checked frequently, investigations and
    alerts less so, and dataset uploads are rare.
    """

    wait_time = between(1, 3)
    host = "http://localhost:8001"
    headers: dict[str, str]

    def on_start(self) -> None:
        """Authenticate and store the JWT token."""
        resp = self.client.post(
            f"{API_PREFIX}/auth/token",
            json={
                "username": DEFAULT_USERNAME,
                "password": DEFAULT_PASSWORD,
            },
            name="POST /auth/token",
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    # ── High-frequency: dashboard & health ───────────────────────────

    @task(10)
    def get_dashboard_stats(self) -> None:
        self.client.get(
            f"{API_PREFIX}/dashboard/stats",
            headers=self.headers,
            name="GET /dashboard/stats",
        )

    @task(5)
    def get_health(self) -> None:
        self.client.get(
            f"{API_PREFIX}/health",
            name="GET /health",
        )

    # ── Medium-frequency: listings ───────────────────────────────────

    @task(6)
    def list_scenarios(self) -> None:
        self.client.get(
            f"{API_PREFIX}/scenarios",
            headers=self.headers,
            name="GET /scenarios",
        )

    @task(6)
    def list_alerts(self) -> None:
        self.client.get(
            f"{API_PREFIX}/alerts",
            headers=self.headers,
            name="GET /alerts",
        )

    @task(6)
    def list_cases(self) -> None:
        self.client.get(
            f"{API_PREFIX}/cases",
            headers=self.headers,
            name="GET /cases",
        )

    @task(4)
    def list_datasets(self) -> None:
        self.client.get(
            f"{API_PREFIX}/datasets",
            headers=self.headers,
            name="GET /datasets",
        )

    # ── Low-frequency: auth introspection ────────────────────────────

    @task(2)
    def get_current_user(self) -> None:
        self.client.get(
            f"{API_PREFIX}/auth/me",
            headers=self.headers,
            name="GET /auth/me",
        )

    @task(2)
    def get_workspace_guide(self) -> None:
        self.client.get(
            f"{API_PREFIX}/workspace/guide",
            headers=self.headers,
            name="GET /workspace/guide",
        )

    # ── Rare: dataset upload (small synthetic payload) ───────────────

    @task(1)
    def upload_small_dataset(self) -> None:
        """Upload a tiny CSV to exercise the ingestion path under load."""
        csv_content = (
            "transaction_id,account_id,amount,timestamp,merchant,category\n"
            "TX-LOAD-001,ACC-001,150.00,2025-01-15T10:00:00,MerchantA,retail\n"
            "TX-LOAD-002,ACC-002,2500.00,2025-01-15T10:05:00,MerchantB,electronics\n"
            "TX-LOAD-003,ACC-001,75.50,2025-01-15T10:10:00,MerchantC,grocery\n"
        )
        self.client.post(
            f"{API_PREFIX}/datasets/upload",
            headers=self.headers,
            files={"file": ("loadtest.csv", csv_content, "text/csv")},
            name="POST /datasets/upload",
        )
