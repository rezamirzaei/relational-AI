"""Benford's Law analysis for transaction amount distributions.

Benford's Law states that in naturally occurring datasets, leading digits
are not uniformly distributed. Digit 1 appears ~30.1% of the time, digit 2
~17.6%, etc. Fraudulent or fabricated data often violates this pattern.
"""

from __future__ import annotations

import math

from relational_fraud_intelligence.domain.models import BenfordDigitResult, UploadedTransaction

# Expected Benford distribution for digits 1-9
BENFORD_EXPECTED = {
    1: 0.30103,
    2: 0.17609,
    3: 0.12494,
    4: 0.09691,
    5: 0.07918,
    6: 0.06695,
    7: 0.05799,
    8: 0.05115,
    9: 0.04576,
}


def _leading_digit(amount: float) -> int | None:
    """Extract the first non-zero digit of a positive number."""
    if amount <= 0:
        return None
    s = f"{amount:.10f}".lstrip("0").lstrip(".")
    for ch in s:
        if ch.isdigit() and ch != "0":
            return int(ch)
    return None


def analyze_benford(
    transactions: list[UploadedTransaction],
) -> tuple[list[BenfordDigitResult], float, float]:
    """Run Benford's Law analysis on transaction amounts.

    Returns:
        (digit_results, chi_squared_statistic, p_value)
    """
    digit_counts: dict[int, int] = {d: 0 for d in range(1, 10)}
    total = 0

    for txn in transactions:
        digit = _leading_digit(txn.amount)
        if digit is not None:
            digit_counts[digit] += 1
            total += 1

    if total < 10:
        # Not enough data for meaningful analysis
        return (
            [
                BenfordDigitResult(
                    digit=d,
                    expected_pct=round(BENFORD_EXPECTED[d] * 100, 2),
                    actual_pct=0.0,
                    deviation=0.0,
                )
                for d in range(1, 10)
            ],
            0.0,
            1.0,
        )

    # Compute chi-squared statistic
    chi_squared = 0.0
    digit_results: list[BenfordDigitResult] = []

    for digit in range(1, 10):
        expected_count = BENFORD_EXPECTED[digit] * total
        observed_count = digit_counts[digit]
        actual_pct = round((observed_count / total) * 100, 2) if total > 0 else 0.0
        expected_pct = round(BENFORD_EXPECTED[digit] * 100, 2)

        if expected_count > 0:
            chi_squared += (observed_count - expected_count) ** 2 / expected_count

        digit_results.append(
            BenfordDigitResult(
                digit=digit,
                expected_pct=expected_pct,
                actual_pct=actual_pct,
                deviation=round(actual_pct - expected_pct, 2),
            )
        )

    # Approximate p-value using chi-squared distribution with 8 degrees of freedom
    # Using the survival function approximation (Wilson–Hilferty)
    p_value = _chi2_survival(chi_squared, df=8)

    return digit_results, round(chi_squared, 4), round(p_value, 6)


def _chi2_survival(x: float, df: int) -> float:
    """Approximate p-value for chi-squared test (no scipy dependency).

    Uses the Wilson–Hilferty normal approximation.
    """
    if x <= 0:
        return 1.0
    if df <= 0:
        return 0.0

    # Wilson-Hilferty transformation to approximate chi-squared CDF
    z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))

    # Standard normal survival function (Abramowitz & Stegun approximation)
    return _normal_survival(z)


def _normal_survival(z: float) -> float:
    """Approximate survival function (1 - CDF) of the standard normal."""
    if z < -8:
        return 1.0
    if z > 8:
        return 0.0

    # Abramowitz & Stegun approximation 7.1.26
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989422804014327  # 1/sqrt(2*pi)
    poly = t * (
        0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
    )
    cdf = 1.0 - d * math.exp(-0.5 * z * z) * poly

    if z >= 0:
        return 1.0 - cdf
    return cdf
