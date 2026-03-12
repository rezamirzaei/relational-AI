"""Tests for the dataset service and statistical fraud analysis engines."""

from __future__ import annotations

import textwrap

import pytest

from relational_fraud_intelligence.application.services.dataset_service import (
    DatasetService,
    DatasetStore,
)
from relational_fraud_intelligence.domain.models import DatasetStatus, RiskLevel


@pytest.fixture()
def service() -> DatasetService:
    return DatasetService(DatasetStore())


VALID_CSV = textwrap.dedent("""\
    transaction_id,account_id,amount,timestamp,merchant,category
    TXN-001,ACCT-001,150.00,2026-03-01 10:00:00,Amazon,retail
    TXN-002,ACCT-001,25.50,2026-03-01 11:00:00,Starbucks,food
    TXN-003,ACCT-002,4500.00,2026-03-01 12:00:00,BestBuy,electronics
    TXN-004,ACCT-002,89.99,2026-03-02 09:00:00,Target,retail
    TXN-005,ACCT-003,1200.00,2026-03-02 10:30:00,CryptoExchange,crypto
    TXN-006,ACCT-001,35.00,2026-03-02 14:00:00,LocalGrocery,food
    TXN-007,ACCT-003,300.00,2026-03-03 08:00:00,Shell,gas
    TXN-008,ACCT-002,15000.00,2026-03-03 09:00:00,GiftCardKiosk,gift_cards
    TXN-009,ACCT-001,42.00,2026-03-03 10:00:00,Uber,transport
    TXN-010,ACCT-003,55.00,2026-03-03 11:00:00,Netflix,entertainment
""")


class TestDatasetUpload:
    def test_upload_valid_csv(self, service: DatasetService) -> None:
        dataset = service.upload_csv("test.csv", VALID_CSV)

        assert dataset.name == "test.csv"
        assert dataset.row_count == 10
        assert dataset.status == DatasetStatus.UPLOADED
        assert dataset.dataset_id

    def test_upload_missing_columns(self, service: DatasetService) -> None:
        bad_csv = "name,value\nfoo,123\n"
        with pytest.raises(ValueError, match="missing required columns"):
            service.upload_csv("bad.csv", bad_csv)

    def test_upload_empty_csv(self, service: DatasetService) -> None:
        empty_csv = "transaction_id,account_id,amount,timestamp\n"
        with pytest.raises(ValueError, match="No valid transactions"):
            service.upload_csv("empty.csv", empty_csv)

    def test_upload_bytes(self, service: DatasetService) -> None:
        dataset = service.upload_csv("test.csv", VALID_CSV.encode("utf-8"))
        assert dataset.row_count == 10

    def test_list_datasets(self, service: DatasetService) -> None:
        service.upload_csv("one.csv", VALID_CSV)
        service.upload_csv("two.csv", VALID_CSV)
        datasets = service.list_datasets()
        assert len(datasets) == 2

    def test_get_dataset_not_found(self, service: DatasetService) -> None:
        with pytest.raises(LookupError):
            service.get_dataset("nonexistent")


class TestDatasetAnalysis:
    def test_analyze_dataset(self, service: DatasetService) -> None:
        dataset = service.upload_csv("test.csv", VALID_CSV)
        result = service.analyze(dataset.dataset_id)

        assert result.dataset_id == dataset.dataset_id
        assert result.total_transactions == 10
        assert result.risk_level in [e.value for e in RiskLevel]
        assert 0 <= result.risk_score <= 100
        assert len(result.benford_digits) == 9
        assert result.summary
        assert result.completed_at

        # Check dataset status updated
        updated = service.get_dataset(dataset.dataset_id)
        assert updated.status == DatasetStatus.COMPLETED

    def test_analyze_nonexistent(self, service: DatasetService) -> None:
        with pytest.raises(LookupError):
            service.analyze("nonexistent")

    def test_benford_digits_cover_all(self, service: DatasetService) -> None:
        dataset = service.upload_csv("test.csv", VALID_CSV)
        result = service.analyze(dataset.dataset_id)
        digits = [d.digit for d in result.benford_digits]
        assert digits == list(range(1, 10))

    def test_outlier_detection_on_large_amount(self, service: DatasetService) -> None:
        """TXN-008 at $15,000 should be flagged as an outlier."""
        dataset = service.upload_csv("test.csv", VALID_CSV)
        result = service.analyze(dataset.dataset_id)

        outlier_ids = [
            a.affected_entity_id
            for a in result.anomalies
            if a.anomaly_type == "statistical-outlier"
        ]
        assert "TXN-008" in outlier_ids

    def test_get_result(self, service: DatasetService) -> None:
        dataset = service.upload_csv("test.csv", VALID_CSV)
        service.analyze(dataset.dataset_id)
        result = service.get_result(dataset.dataset_id)
        assert result.total_transactions == 10

    def test_get_result_not_found(self, service: DatasetService) -> None:
        dataset = service.upload_csv("test.csv", VALID_CSV)
        with pytest.raises(LookupError):
            service.get_result(dataset.dataset_id)


class TestTransactionIngestion:
    def test_ingest_via_api(self, service: DatasetService) -> None:
        transactions = [
            {
                "transaction_id": "T1",
                "account_id": "A1",
                "amount": 100,
                "timestamp": "2026-03-01 10:00:00",
            },
            {
                "transaction_id": "T2",
                "account_id": "A1",
                "amount": 200,
                "timestamp": "2026-03-01 11:00:00",
            },
        ]
        dataset = service.ingest_transactions("api-test", transactions)
        assert dataset.row_count == 2
        assert dataset.name == "api-test"

    def test_ingest_empty_raises(self, service: DatasetService) -> None:
        with pytest.raises(ValueError, match="No valid transactions"):
            service.ingest_transactions("empty", [])


class TestSampleDataset:
    """Test that the shipped sample CSV works with the analysis pipeline."""

    def test_analyze_sample_csv(self, service: DatasetService) -> None:
        import pathlib

        sample_path = (
            pathlib.Path(__file__).resolve().parent.parent
            / "docs"
            / "sample_data"
            / "sample_transactions.csv"
        )
        if not sample_path.exists():
            pytest.skip("Sample CSV not generated yet")

        content = sample_path.read_text()
        dataset = service.upload_csv("sample_transactions.csv", content)
        assert dataset.row_count > 800

        result = service.analyze(dataset.dataset_id)
        assert result.total_transactions > 800
        assert result.total_anomalies > 0, "Sample dataset should have planted anomalies"
        assert result.risk_score > 0
        assert result.summary

        # Check that at least some anomaly types were detected
        anomaly_types = {a.anomaly_type for a in result.anomalies}
        assert len(anomaly_types) >= 1, f"Expected multiple anomaly types, got {anomaly_types}"
