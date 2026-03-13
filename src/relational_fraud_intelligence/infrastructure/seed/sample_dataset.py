"""Generate a coherent sample transaction CSV with realistic planted patterns.

Run this module to regenerate ``docs/sample_data/sample_transactions.csv``.
"""

from __future__ import annotations

import csv
import io
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TypedDict

random.seed(42)


class MerchantProfile(TypedDict):
    category: str
    channel_bias: tuple[str, ...]
    country: str
    mean_amount: float
    stddev_amount: float


class AccountProfile(TypedDict):
    devices: list[str]
    home_country: str


MERCHANTS: dict[str, MerchantProfile] = {
    "Amazon": {
        "category": "retail",
        "country": "US",
        "channel_bias": ("card-not-present", "wallet"),
        "mean_amount": 84.0,
        "stddev_amount": 45.0,
    },
    "Walmart": {
        "category": "retail",
        "country": "US",
        "channel_bias": ("card-present", "card-not-present"),
        "mean_amount": 72.0,
        "stddev_amount": 38.0,
    },
    "Target": {
        "category": "retail",
        "country": "US",
        "channel_bias": ("card-present", "wallet"),
        "mean_amount": 69.0,
        "stddev_amount": 35.0,
    },
    "BestBuy": {
        "category": "electronics",
        "country": "US",
        "channel_bias": ("card-present", "card-not-present"),
        "mean_amount": 210.0,
        "stddev_amount": 110.0,
    },
    "Starbucks": {
        "category": "food",
        "country": "US",
        "channel_bias": ("card-present", "wallet"),
        "mean_amount": 12.0,
        "stddev_amount": 6.0,
    },
    "Shell-Gas": {
        "category": "gas",
        "country": "US",
        "channel_bias": ("card-present", "wallet"),
        "mean_amount": 58.0,
        "stddev_amount": 24.0,
    },
    "Uber": {
        "category": "transport",
        "country": "US",
        "channel_bias": ("card-not-present", "wallet"),
        "mean_amount": 28.0,
        "stddev_amount": 14.0,
    },
    "Netflix": {
        "category": "entertainment",
        "country": "US",
        "channel_bias": ("card-not-present",),
        "mean_amount": 17.0,
        "stddev_amount": 4.0,
    },
    "Spotify": {
        "category": "entertainment",
        "country": "US",
        "channel_bias": ("card-not-present",),
        "mean_amount": 15.0,
        "stddev_amount": 3.5,
    },
    "PharmacyOne": {
        "category": "health",
        "country": "US",
        "channel_bias": ("card-present", "card-not-present"),
        "mean_amount": 42.0,
        "stddev_amount": 18.0,
    },
    "CryptoExchange-X": {
        "category": "crypto",
        "country": "EE",
        "channel_bias": ("wallet", "bank-transfer"),
        "mean_amount": 950.0,
        "stddev_amount": 520.0,
    },
    "GiftCardKiosk-A": {
        "category": "gift_cards",
        "country": "NL",
        "channel_bias": ("card-not-present", "wallet"),
        "mean_amount": 640.0,
        "stddev_amount": 260.0,
    },
    "DigitalGoods-Z": {
        "category": "digital_goods",
        "country": "SG",
        "channel_bias": ("card-not-present", "wallet"),
        "mean_amount": 410.0,
        "stddev_amount": 180.0,
    },
    "HotelChain": {
        "category": "travel",
        "country": "US",
        "channel_bias": ("card-not-present",),
        "mean_amount": 240.0,
        "stddev_amount": 120.0,
    },
    "AirlineTickets": {
        "category": "travel",
        "country": "US",
        "channel_bias": ("card-not-present",),
        "mean_amount": 380.0,
        "stddev_amount": 140.0,
    },
    "UtilityPay": {
        "category": "utilities",
        "country": "US",
        "channel_bias": ("ach", "bank-transfer"),
        "mean_amount": 116.0,
        "stddev_amount": 54.0,
    },
}

NORMAL_MERCHANTS = tuple(
    name
    for name, profile in MERCHANTS.items()
    if profile["category"] not in {"crypto", "gift_cards"}
)
HIGH_RISK_MERCHANTS = ("CryptoExchange-X", "GiftCardKiosk-A", "DigitalGoods-Z")

CHANNELS = ["card-not-present", "card-present", "wallet", "bank-transfer", "ach"]
COUNTRY_POOL = ("US", "US", "US", "US", "GB", "CA")

ACCOUNTS = [f"ACCT-{i:04d}" for i in range(1, 51)]
ACCOUNT_PROFILES: dict[str, AccountProfile] = {
    account_id: {
        "home_country": random.choice(COUNTRY_POOL),
        "devices": [f"fp-{index + 1:04d}", f"fp-{index + 101:04d}"],
    }
    for index, account_id in enumerate(ACCOUNTS)
}


def _sample_amount(merchant: str) -> float:
    profile = MERCHANTS[merchant]
    amount = random.gauss(profile["mean_amount"], profile["stddev_amount"])
    return round(max(1.5, amount), 2)


def _pick_channel(merchant: str) -> str:
    profile = MERCHANTS[merchant]
    primary = random.choice(profile["channel_bias"])
    if random.random() < 0.75:
        return primary
    return random.choice(CHANNELS)


def _build_row(
    *,
    transaction_id: str,
    account_id: str,
    merchant: str,
    timestamp: datetime,
    amount: float,
    device_fingerprint: str,
    ip_country: str,
    channel: str | None = None,
    is_fraud: bool = False,
) -> dict[str, str]:
    merchant_profile = MERCHANTS[merchant]
    return {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "amount": f"{amount:.2f}",
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "merchant": merchant,
        "category": merchant_profile["category"],
        "device_fingerprint": device_fingerprint,
        "ip_country": ip_country,
        "channel": channel or _pick_channel(merchant),
        "is_fraud": "1" if is_fraud else "0",
    }


def _generate_normal_transactions(n: int, base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for offset in range(n):
        account_id = random.choice(ACCOUNTS)
        account_profile = ACCOUNT_PROFILES[account_id]
        merchant = random.choice(NORMAL_MERCHANTS)
        timestamp = base_time + timedelta(
            days=random.uniform(0, 30),
            hours=random.uniform(6, 23),
            minutes=random.randint(0, 59),
        )
        rows.append(
            _build_row(
                transaction_id=f"TXN-{10000 + offset}",
                account_id=account_id,
                merchant=merchant,
                timestamp=timestamp,
                amount=_sample_amount(merchant),
                device_fingerprint=random.choice(account_profile["devices"]),
                ip_country=account_profile["home_country"],
                is_fraud=False,
            )
        )
    return rows


def _generate_shared_device_ring(base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    accounts = ["ACCT-0008", "ACCT-0016", "ACCT-0031"]
    shared_device = "fp-ring-shared-01"
    merchants = ["GiftCardKiosk-A", "CryptoExchange-X", "DigitalGoods-Z"]

    for index in range(12):
        account_id = accounts[index % len(accounts)]
        merchant = merchants[index % len(merchants)]
        timestamp = base_time + timedelta(days=13, hours=2, minutes=index * 7)
        rows.append(
            _build_row(
                transaction_id=f"TXN-RING-{index}",
                account_id=account_id,
                merchant=merchant,
                timestamp=timestamp,
                amount=round(random.uniform(520.0, 1650.0), 2),
                device_fingerprint=shared_device,
                ip_country=random.choice(["NL", "DE", "US"]),
                channel="wallet",
                is_fraud=True,
            )
        )
    return rows


def _generate_geo_takeover(base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    account_id = "ACCT-0025"
    account_profile = ACCOUNT_PROFILES[account_id]

    for index in range(6):
        timestamp = base_time + timedelta(days=18, hours=1, minutes=index * 11)
        merchant = random.choice(["CryptoExchange-X", "HotelChain", "AirlineTickets"])
        rows.append(
            _build_row(
                transaction_id=f"TXN-GEO-{index}",
                account_id=account_id,
                merchant=merchant,
                timestamp=timestamp,
                amount=round(random.uniform(780.0, 4200.0), 2),
                device_fingerprint="fp-prague-emulator-77",
                ip_country=random.choice(["CZ", "RU"]),
                channel="card-not-present",
                is_fraud=True,
            )
        )

    # Keep the account's baseline behavior coherent before the drift.
    for index in range(4):
        timestamp = base_time + timedelta(days=7, hours=8, minutes=index * 42)
        rows.append(
            _build_row(
                transaction_id=f"TXN-GEO-BASE-{index}",
                account_id=account_id,
                merchant=random.choice(["Uber", "Amazon", "UtilityPay"]),
                timestamp=timestamp,
                amount=round(random.uniform(18.0, 140.0), 2),
                device_fingerprint=random.choice(account_profile["devices"]),
                ip_country=account_profile["home_country"],
                channel=random.choice(("wallet", "card-not-present", "ach")),
                is_fraud=False,
            )
        )
    return rows


def _generate_round_amount_structuring(base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    account_id = "ACCT-0040"
    for index, amount in enumerate((500, 900, 1000, 1500, 2000, 2500, 3000, 4500)):
        timestamp = base_time + timedelta(days=random.uniform(3, 26), hours=random.uniform(9, 17))
        rows.append(
            _build_row(
                transaction_id=f"TXN-ROUND-{index}",
                account_id=account_id,
                merchant="GiftCardKiosk-A",
                timestamp=timestamp,
                amount=float(amount),
                device_fingerprint="fp-round-struct-01",
                ip_country="US",
                channel="card-not-present",
                is_fraud=True,
            )
        )
    return rows


def _generate_velocity_burst(base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    account_id = "ACCT-0008"
    burst_start = base_time + timedelta(days=15, hours=2)

    for index in range(12):
        timestamp = burst_start + timedelta(minutes=random.randint(0, 95))
        rows.append(
            _build_row(
                transaction_id=f"TXN-VELOCITY-{index}",
                account_id=account_id,
                merchant=random.choice(HIGH_RISK_MERCHANTS),
                timestamp=timestamp,
                amount=round(random.uniform(220.0, 980.0), 2),
                device_fingerprint="fp-ring-shared-01",
                ip_country="RU",
                channel="wallet",
                is_fraud=True,
            )
        )
    return rows


def _generate_benford_violation_batch(base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    account_id = "ACCT-0031"
    for index in range(20):
        leading = random.choice([5, 5, 6, 7, 8, 9, 9])
        amount = round(leading * 100 + random.uniform(0.0, 99.99), 2)
        timestamp = base_time + timedelta(days=random.uniform(0, 30), hours=random.uniform(6, 23))
        merchant = random.choice(["GiftCardKiosk-A", "DigitalGoods-Z", "CryptoExchange-X"])
        rows.append(
            _build_row(
                transaction_id=f"TXN-BENFORD-{index}",
                account_id=account_id,
                merchant=merchant,
                timestamp=timestamp,
                amount=amount,
                device_fingerprint="fp-ring-shared-01" if index % 2 == 0 else "fp-benford-aux-1",
                ip_country="US" if index % 4 else "NL",
                channel=random.choice(("wallet", "card-not-present", "bank-transfer")),
                is_fraud=True,
            )
        )
    return rows


def _generate_outlier_transactions(base_time: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    accounts = ["ACCT-0017", "ACCT-0046", "ACCT-0049"]
    for index, account_id in enumerate(accounts):
        for burst in range(2):
            timestamp = base_time + timedelta(
                days=random.uniform(5, 25), hours=random.uniform(1, 4)
            )
            merchant = random.choice(["CryptoExchange-X", "DigitalGoods-Z"])
            rows.append(
                _build_row(
                    transaction_id=f"TXN-OUTLIER-{index * 10 + burst}",
                    account_id=account_id,
                    merchant=merchant,
                    timestamp=timestamp,
                    amount=round(random.uniform(8500.0, 25000.0), 2),
                    device_fingerprint=f"fp-suspicious-{index}",
                    ip_country=random.choice(["NG", "RU", "CN"]),
                    channel="card-not-present",
                    is_fraud=True,
                )
            )
    return rows


def generate_sample_csv() -> str:
    base_time = datetime(2026, 2, 1, tzinfo=UTC)
    rows: list[dict[str, str]] = []
    rows.extend(_generate_normal_transactions(780, base_time))
    rows.extend(_generate_shared_device_ring(base_time))
    rows.extend(_generate_geo_takeover(base_time))
    rows.extend(_generate_round_amount_structuring(base_time))
    rows.extend(_generate_velocity_burst(base_time))
    rows.extend(_generate_benford_violation_batch(base_time))
    rows.extend(_generate_outlier_transactions(base_time))

    # Ensure normal behavior is internally consistent before shuffling.
    by_account: dict[str, int] = defaultdict(int)
    for row in rows:
        by_account[row["account_id"]] += 1

    random.shuffle(rows)

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
    writer.writerows(rows)
    return output.getvalue()


if __name__ == "__main__":
    import pathlib

    output_dir = (
        pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent / "docs" / "sample_data"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sample_transactions.csv"
    output_path.write_text(generate_sample_csv())
    print(f"Generated {output_path} with ~842 transactions")
