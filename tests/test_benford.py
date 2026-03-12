"""Tests for Benford's Law analysis engine."""

from __future__ import annotations

from datetime import UTC, datetime

from relational_fraud_intelligence.domain.models import UploadedTransaction
from relational_fraud_intelligence.infrastructure.analysis.benford import analyze_benford


def _make_txn(row: int, amount: float) -> UploadedTransaction:
    return UploadedTransaction(
        row_index=row,
        transaction_id=f"txn-{row}",
        account_id="A1",
        amount=amount,
        timestamp=datetime(2026, 3, 1, tzinfo=UTC),
    )


class TestBenford:
    def test_returns_nine_digits(self) -> None:
        transactions = [_make_txn(i, 100 + i * 37.5) for i in range(50)]
        digits, chi_sq, p_value = analyze_benford(transactions)
        assert len(digits) == 9
        assert digits[0].digit == 1
        assert digits[8].digit == 9

    def test_empty_transactions(self) -> None:
        digits, chi_sq, p_value = analyze_benford([])
        assert len(digits) == 9
        assert chi_sq == 0.0
        assert p_value == 1.0

    def test_few_transactions_returns_safe_defaults(self) -> None:
        transactions = [_make_txn(i, 10 + i) for i in range(5)]
        digits, chi_sq, p_value = analyze_benford(transactions)
        assert p_value == 1.0  # Not enough data to flag

    def test_natural_distribution_not_suspicious(self) -> None:
        """Log-normal amounts should roughly follow Benford's Law."""
        import random

        random.seed(12345)
        transactions = [_make_txn(i, round(random.lognormvariate(4, 1.5), 2)) for i in range(500)]
        digits, chi_sq, p_value = analyze_benford(transactions)
        # Should NOT be flagged — natural data
        assert p_value > 0.01, f"Expected non-suspicious p-value, got {p_value}"

    def test_uniform_distribution_is_suspicious(self) -> None:
        """Uniformly distributed amounts should violate Benford's Law."""
        import random

        random.seed(99999)
        transactions = [_make_txn(i, round(random.uniform(100, 999), 2)) for i in range(500)]
        digits, chi_sq, p_value = analyze_benford(transactions)
        # Uniform distribution should be flagged
        assert p_value < 0.05, f"Expected suspicious p-value, got {p_value}"
        assert chi_sq > 10
