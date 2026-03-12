"""Generate a realistic sample transaction CSV with planted fraud anomalies.

Run this module to regenerate docs/sample_data/sample_transactions.csv.
"""

from __future__ import annotations

import csv
import io
import random
from datetime import UTC, datetime, timedelta

# Reproducible seed
random.seed(42)

ACCOUNTS = [f"ACCT-{i:04d}" for i in range(1, 51)]  # 50 accounts
MERCHANTS = [
    "Amazon",
    "Walmart",
    "Target",
    "BestBuy",
    "Starbucks",
    "Shell-Gas",
    "Uber",
    "Netflix",
    "Spotify",
    "Steam",
    "CryptoExchange-X",
    "GiftCardKiosk-A",
    "DigitalGoods-Z",
    "LocalGrocery",
    "PharmacyOne",
    "RestaurantRow",
    "AirlineTickets",
    "HotelChain",
    "UtilityPay",
    "InsuranceCo",
]
CATEGORIES = [
    "retail",
    "food",
    "gas",
    "transport",
    "entertainment",
    "digital_goods",
    "crypto",
    "gift_cards",
    "travel",
    "utilities",
]
CHANNELS = ["card-not-present", "card-present", "wallet", "bank-transfer", "ach"]
COUNTRIES = ["US", "US", "US", "US", "GB", "CA", "DE", "NG", "RU", "CN"]


def _benford_amount() -> float:
    """Generate amount following Benford's Law (natural log-normal)."""
    return round(random.lognormvariate(4.5, 1.5), 2)


def _generate_normal_transactions(n: int, base_time: datetime) -> list[dict[str, str]]:
    """Generate n normal-looking transactions spread over 30 days."""
    rows: list[dict[str, str]] = []
    for i in range(n):
        acct = random.choice(ACCOUNTS)
        merchant = random.choice(MERCHANTS[:15])  # Normal merchants
        ts = base_time + timedelta(
            days=random.uniform(0, 30),
            hours=random.uniform(8, 22),
            minutes=random.randint(0, 59),
        )
        amount = _benford_amount()
        amount = max(1.50, min(amount, 5000.0))

        rows.append(
            {
                "transaction_id": f"TXN-{10000 + i}",
                "account_id": acct,
                "amount": f"{amount:.2f}",
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": merchant,
                "category": random.choice(CATEGORIES[:7]),
                "device_fingerprint": f"fp-{random.randint(1, 200):04d}",
                "ip_country": random.choice(COUNTRIES[:5]),
                "channel": random.choice(CHANNELS),
                "is_fraud": "0",
            }
        )
    return rows


def _generate_outlier_transactions(base_time: datetime) -> list[dict[str, str]]:
    """Plant statistical outlier transactions (abnormally large amounts)."""
    rows: list[dict[str, str]] = []
    fraud_accounts = random.sample(ACCOUNTS, 3)

    for j, acct in enumerate(fraud_accounts):
        for k in range(2):
            ts = base_time + timedelta(days=random.uniform(5, 25), hours=random.uniform(1, 4))
            amount = random.uniform(8000, 25000)  # Way above normal
            rows.append(
                {
                    "transaction_id": f"TXN-OUTLIER-{j * 10 + k}",
                    "account_id": acct,
                    "amount": f"{amount:.2f}",
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "merchant": random.choice(MERCHANTS[10:13]),  # Suspicious merchants
                    "category": random.choice(["crypto", "gift_cards", "digital_goods"]),
                    "device_fingerprint": f"fp-suspicious-{j}",
                    "ip_country": random.choice(["NG", "RU", "CN"]),
                    "channel": "card-not-present",
                    "is_fraud": "1",
                }
            )
    return rows


def _generate_velocity_burst(base_time: datetime) -> list[dict[str, str]]:
    """Plant a velocity spike — many transactions in a short window."""
    rows: list[dict[str, str]] = []
    acct = ACCOUNTS[7]
    burst_start = base_time + timedelta(days=15, hours=2)

    for k in range(12):  # 12 transactions in 2 hours
        ts = burst_start + timedelta(minutes=random.randint(0, 120))
        amount = random.uniform(200, 800)
        rows.append(
            {
                "transaction_id": f"TXN-VELOCITY-{k}",
                "account_id": acct,
                "amount": f"{amount:.2f}",
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": random.choice(MERCHANTS[10:13]),
                "category": "digital_goods",
                "device_fingerprint": "fp-burst-device",
                "ip_country": "RU",
                "channel": "wallet",
                "is_fraud": "1",
            }
        )
    return rows


def _generate_round_amount_structuring(base_time: datetime) -> list[dict[str, str]]:
    """Plant round-amount structuring pattern."""
    rows: list[dict[str, str]] = []
    acct = ACCOUNTS[15]

    for k in range(8):
        ts = base_time + timedelta(days=random.uniform(1, 28), hours=random.uniform(9, 17))
        # All round amounts just under reporting thresholds
        amount = random.choice([500, 900, 1000, 1500, 2000, 2500, 3000, 4500])
        rows.append(
            {
                "transaction_id": f"TXN-ROUND-{k}",
                "account_id": acct,
                "amount": f"{amount:.2f}",
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": random.choice(MERCHANTS[:5]),
                "category": "retail",
                "device_fingerprint": f"fp-round-{k % 2}",
                "ip_country": "US",
                "channel": "card-present",
                "is_fraud": "1",
            }
        )
    return rows


def _generate_benford_violation_batch(base_time: datetime) -> list[dict[str, str]]:
    """Generate transactions that deliberately violate Benford's Law.

    Overrepresents leading digit 5 and 9, underrepresents digit 1.
    """
    rows: list[dict[str, str]] = []
    acct = ACCOUNTS[30]

    for k in range(20):
        # Force leading digits 5-9
        leading = random.choice([5, 5, 6, 7, 8, 9, 9])
        rest = random.uniform(0, 99.99)
        amount = leading * 100 + rest
        ts = base_time + timedelta(days=random.uniform(0, 30), hours=random.uniform(6, 23))

        rows.append(
            {
                "transaction_id": f"TXN-BENFORD-{k}",
                "account_id": acct,
                "amount": f"{amount:.2f}",
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": random.choice(MERCHANTS),
                "category": random.choice(CATEGORIES),
                "device_fingerprint": f"fp-benford-{k % 3}",
                "ip_country": "US",
                "channel": random.choice(CHANNELS),
                "is_fraud": "1",
            }
        )
    return rows


def generate_sample_csv() -> str:
    """Generate a complete sample CSV as a string."""
    base_time = datetime(2026, 2, 1, tzinfo=UTC)

    all_rows: list[dict[str, str]] = []
    all_rows.extend(_generate_normal_transactions(800, base_time))
    all_rows.extend(_generate_outlier_transactions(base_time))
    all_rows.extend(_generate_velocity_burst(base_time))
    all_rows.extend(_generate_round_amount_structuring(base_time))
    all_rows.extend(_generate_benford_violation_batch(base_time))

    # Shuffle to mix fraud with normal
    random.shuffle(all_rows)

    output = io.StringIO()
    fieldnames = [
        "transaction_id",
        "account_id",
        "amount",
        "timestamp",
        "merchant",
        "category",
        "device_fingerprint",
        "ip_country",
        "channel",
        "is_fraud",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)
    return output.getvalue()


if __name__ == "__main__":
    import pathlib

    out_dir = (
        pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent / "docs" / "sample_data"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sample_transactions.csv"
    out_path.write_text(generate_sample_csv())
    print(f"Generated {out_path} with ~846 transactions")
