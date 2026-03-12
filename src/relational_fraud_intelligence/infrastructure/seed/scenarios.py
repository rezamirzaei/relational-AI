from __future__ import annotations

from datetime import datetime

from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    FraudScenario,
    InvestigatorNote,
    MerchantProfile,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_seed_scenarios() -> tuple[FraudScenario, ...]:
    synthetic_identity_ring = FraudScenario(
        scenario_id="synthetic-identity-ring",
        title="Synthetic Identity Gift Card Ring",
        industry="Fintech",
        summary=(
            "Recently opened checking accounts are cashing out through a gift card reseller "
            "from a shared low-trust device cluster."
        ),
        hypothesis=(
            "A synthetic identity ring is onboarding thin-file customers, sharing devices, "
            "and liquidating value through high-risk digital goods merchants."
        ),
        tags=[
            ScenarioTag.FRAUD,
            ScenarioTag.SYNTHETIC_IDENTITY,
            ScenarioTag.DEVICE_RING,
            ScenarioTag.CROSS_BORDER,
        ],
        customers=[
            CustomerProfile(
                customer_id="cust_amina",
                full_name="Amina Rahman",
                country_code="US",
                segment="consumer-checking",
                declared_income_band="$40k-$60k",
                linked_account_ids=["acct_amina"],
                linked_device_ids=["dev_shared_1"],
                watchlist_tags=["thin-file", "kyc-document-risk"],
            ),
            CustomerProfile(
                customer_id="cust_noah",
                full_name="Noah Carter",
                country_code="US",
                segment="consumer-checking",
                declared_income_band="$30k-$50k",
                linked_account_ids=["acct_noah"],
                linked_device_ids=["dev_shared_1", "dev_burner_9"],
                watchlist_tags=["address-mismatch", "identity-velocity"],
            ),
        ],
        accounts=[
            AccountProfile(
                account_id="acct_amina",
                customer_id="cust_amina",
                opened_at=_dt("2026-02-25T09:15:00"),
                current_balance=820.0,
                average_monthly_inflow=2100.0,
                chargeback_count=1,
                manual_review_count=2,
            ),
            AccountProfile(
                account_id="acct_noah",
                customer_id="cust_noah",
                opened_at=_dt("2026-02-28T12:20:00"),
                current_balance=610.0,
                average_monthly_inflow=1800.0,
                chargeback_count=2,
                manual_review_count=3,
            ),
        ],
        devices=[
            DeviceProfile(
                device_id="dev_shared_1",
                fingerprint="fp-shared-lenovo-001",
                ip_country_code="US",
                linked_customer_ids=["cust_amina", "cust_noah"],
                trust_score=0.19,
            ),
            DeviceProfile(
                device_id="dev_burner_9",
                fingerprint="fp-burner-android-774",
                ip_country_code="NL",
                linked_customer_ids=["cust_noah"],
                trust_score=0.11,
            ),
        ],
        merchants=[
            MerchantProfile(
                merchant_id="merch_giftloop",
                display_name="GiftLoop Digital Vault",
                country_code="NL",
                category="digital_goods",
                description="Bulk digital gift card marketplace with instant resale routing.",
            ),
            MerchantProfile(
                merchant_id="merch_streamarc",
                display_name="StreamArc Media",
                country_code="US",
                category="subscription",
                description="Streaming bundle seller with frequent card testing indicators.",
            ),
        ],
        transactions=[
            TransactionRecord(
                transaction_id="txn_1001",
                customer_id="cust_amina",
                account_id="acct_amina",
                device_id="dev_shared_1",
                merchant_id="merch_giftloop",
                occurred_at=_dt("2026-03-08T14:03:00"),
                amount=1250.0,
                currency="USD",
                channel=TransactionChannel.CARD_NOT_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
            TransactionRecord(
                transaction_id="txn_1002",
                customer_id="cust_amina",
                account_id="acct_amina",
                device_id="dev_shared_1",
                merchant_id="merch_giftloop",
                occurred_at=_dt("2026-03-08T14:07:00"),
                amount=1125.0,
                currency="USD",
                channel=TransactionChannel.CARD_NOT_PRESENT,
                status=TransactionStatus.REVIEW,
            ),
            TransactionRecord(
                transaction_id="txn_1003",
                customer_id="cust_noah",
                account_id="acct_noah",
                device_id="dev_shared_1",
                merchant_id="merch_giftloop",
                occurred_at=_dt("2026-03-08T14:09:00"),
                amount=980.0,
                currency="USD",
                channel=TransactionChannel.WALLET,
                status=TransactionStatus.REVIEW,
            ),
            TransactionRecord(
                transaction_id="txn_1004",
                customer_id="cust_noah",
                account_id="acct_noah",
                device_id="dev_burner_9",
                merchant_id="merch_giftloop",
                occurred_at=_dt("2026-03-08T14:16:00"),
                amount=1410.0,
                currency="USD",
                channel=TransactionChannel.CARD_NOT_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
            TransactionRecord(
                transaction_id="txn_1005",
                customer_id="cust_noah",
                account_id="acct_noah",
                device_id="dev_burner_9",
                merchant_id="merch_streamarc",
                occurred_at=_dt("2026-03-09T10:02:00"),
                amount=24.99,
                currency="USD",
                channel=TransactionChannel.CARD_NOT_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
        ],
        investigator_notes=[
            InvestigatorNote(
                note_id="note_2001",
                subject_customer_id="cust_amina",
                author="risk.ops@bank.example",
                created_at=_dt("2026-03-08T15:00:00"),
                body=(
                    "Manual review found a shared device fingerprint across two new identities. "
                    "Gift card liquidation pattern suggests synthetic identity behavior."
                ),
            ),
            InvestigatorNote(
                note_id="note_2002",
                subject_customer_id="cust_noah",
                author="fraud.analyst@bank.example",
                created_at=_dt("2026-03-09T09:30:00"),
                body=(
                    "Second profile used a burner Android after verification failure. "
                    "Behavior is consistent with mule-style cash out through digital goods."
                ),
            ),
        ],
    )

    account_takeover = FraudScenario(
        scenario_id="travel-ato-escalation",
        title="Travel Account Takeover Escalation",
        industry="Digital Banking",
        summary=(
            "A premium customer shifts to an emulator device in Prague and starts a rapid burst "
            "of cross-border travel and payout activity."
        ),
        hypothesis=(
            "Credential stuffing or a SIM swap led to account takeover and a rapid spend burst "
            "from a new foreign device."
        ),
        tags=[
            ScenarioTag.FRAUD,
            ScenarioTag.ACCOUNT_TAKEOVER,
            ScenarioTag.CROSS_BORDER,
        ],
        customers=[
            CustomerProfile(
                customer_id="cust_olivia",
                full_name="Olivia Chen",
                country_code="US",
                segment="premium-checking",
                declared_income_band="$120k-$150k",
                linked_account_ids=["acct_olivia"],
                linked_device_ids=["dev_known_olivia", "dev_unknown_prague"],
                watchlist_tags=["mfa-reset-request"],
            ),
        ],
        accounts=[
            AccountProfile(
                account_id="acct_olivia",
                customer_id="cust_olivia",
                opened_at=_dt("2021-06-11T08:00:00"),
                current_balance=19450.0,
                average_monthly_inflow=11600.0,
                chargeback_count=0,
                manual_review_count=1,
            ),
        ],
        devices=[
            DeviceProfile(
                device_id="dev_known_olivia",
                fingerprint="fp-iphone-olivia-002",
                ip_country_code="US",
                linked_customer_ids=["cust_olivia"],
                trust_score=0.93,
            ),
            DeviceProfile(
                device_id="dev_unknown_prague",
                fingerprint="fp-emulator-prg-443",
                ip_country_code="CZ",
                linked_customer_ids=["cust_olivia"],
                trust_score=0.08,
            ),
        ],
        merchants=[
            MerchantProfile(
                merchant_id="merch_airlift",
                display_name="Airlift Tickets",
                country_code="CZ",
                category="travel",
                description="Instant delivery travel booking platform.",
            ),
            MerchantProfile(
                merchant_id="merch_wirez",
                display_name="Wirez Transfer Hub",
                country_code="LT",
                category="money_transfer",
                description="Cross-border payout processor often used for rapid disbursement.",
            ),
        ],
        transactions=[
            TransactionRecord(
                transaction_id="txn_2001",
                customer_id="cust_olivia",
                account_id="acct_olivia",
                device_id="dev_unknown_prague",
                merchant_id="merch_airlift",
                occurred_at=_dt("2026-03-10T18:14:00"),
                amount=1980.0,
                currency="USD",
                channel=TransactionChannel.CARD_NOT_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
            TransactionRecord(
                transaction_id="txn_2002",
                customer_id="cust_olivia",
                account_id="acct_olivia",
                device_id="dev_unknown_prague",
                merchant_id="merch_wirez",
                occurred_at=_dt("2026-03-10T18:19:00"),
                amount=2400.0,
                currency="USD",
                channel=TransactionChannel.BANK_TRANSFER,
                status=TransactionStatus.REVIEW,
            ),
            TransactionRecord(
                transaction_id="txn_2003",
                customer_id="cust_olivia",
                account_id="acct_olivia",
                device_id="dev_unknown_prague",
                merchant_id="merch_wirez",
                occurred_at=_dt("2026-03-10T18:22:00"),
                amount=2600.0,
                currency="USD",
                channel=TransactionChannel.BANK_TRANSFER,
                status=TransactionStatus.REVIEW,
            ),
        ],
        investigator_notes=[
            InvestigatorNote(
                note_id="note_3001",
                subject_customer_id="cust_olivia",
                author="security@bank.example",
                created_at=_dt("2026-03-10T18:40:00"),
                body=(
                    "Customer reported a possible SIM swap and could not access MFA. "
                    "New emulator device initiated cross-border travel and transfer "
                    "spend within minutes."
                ),
            ),
        ],
    )

    payroll_mule_funnel = FraudScenario(
        scenario_id="payroll-mule-funnel",
        title="Payroll Mule Funnel Through Transfer Network",
        industry="Business Banking",
        summary=(
            "A small staffing business receives payroll funds and rapidly fans them out to "
            "consumer accounts linked to the same residential device cluster."
        ),
        hypothesis=(
            "A first-party fraud actor is using a payroll front to route funds to money mule "
            "accounts and convert proceeds through transfer and crypto rails."
        ),
        tags=[
            ScenarioTag.FRAUD,
            ScenarioTag.DEVICE_RING,
            ScenarioTag.CROSS_BORDER,
        ],
        customers=[
            CustomerProfile(
                customer_id="cust_javier",
                full_name="Javier Solis",
                country_code="US",
                segment="small-business-checking",
                declared_income_band="$250k-$500k",
                linked_account_ids=["acct_javier_biz"],
                linked_device_ids=["dev_rowhouse_hub"],
                watchlist_tags=["beneficiary-velocity", "recent-password-reset"],
            ),
            CustomerProfile(
                customer_id="cust_marisol",
                full_name="Marisol Vega",
                country_code="US",
                segment="consumer-checking",
                declared_income_band="$25k-$40k",
                linked_account_ids=["acct_marisol"],
                linked_device_ids=["dev_rowhouse_hub"],
                watchlist_tags=["beneficiary-onboarding"],
            ),
            CustomerProfile(
                customer_id="cust_terrence",
                full_name="Terrence Hall",
                country_code="US",
                segment="consumer-checking",
                declared_income_band="$35k-$55k",
                linked_account_ids=["acct_terrence"],
                linked_device_ids=["dev_rowhouse_hub", "dev_cafe_proxy"],
                watchlist_tags=["cash-out-pattern"],
            ),
        ],
        accounts=[
            AccountProfile(
                account_id="acct_javier_biz",
                customer_id="cust_javier",
                opened_at=_dt("2023-04-19T10:30:00"),
                current_balance=98200.0,
                average_monthly_inflow=78400.0,
                chargeback_count=0,
                manual_review_count=2,
            ),
            AccountProfile(
                account_id="acct_marisol",
                customer_id="cust_marisol",
                opened_at=_dt("2025-12-02T16:10:00"),
                current_balance=420.0,
                average_monthly_inflow=2100.0,
                chargeback_count=1,
                manual_review_count=1,
            ),
            AccountProfile(
                account_id="acct_terrence",
                customer_id="cust_terrence",
                opened_at=_dt("2025-11-18T13:00:00"),
                current_balance=310.0,
                average_monthly_inflow=1950.0,
                chargeback_count=1,
                manual_review_count=2,
            ),
        ],
        devices=[
            DeviceProfile(
                device_id="dev_rowhouse_hub",
                fingerprint="fp-windows-rowhouse-115",
                ip_country_code="US",
                linked_customer_ids=["cust_javier", "cust_marisol", "cust_terrence"],
                trust_score=0.22,
            ),
            DeviceProfile(
                device_id="dev_cafe_proxy",
                fingerprint="fp-proxy-cafe-991",
                ip_country_code="RO",
                linked_customer_ids=["cust_terrence"],
                trust_score=0.14,
            ),
        ],
        merchants=[
            MerchantProfile(
                merchant_id="merch_remitline",
                display_name="RemitLine Exchange",
                country_code="MX",
                category="money_transfer",
                description="Cross-border payout and remittance processor.",
            ),
            MerchantProfile(
                merchant_id="merch_coinstack",
                display_name="CoinStack OTC",
                country_code="EE",
                category="crypto",
                description="Over-the-counter crypto conversion desk with instant settlement.",
            ),
        ],
        transactions=[
            TransactionRecord(
                transaction_id="txn_3001",
                customer_id="cust_javier",
                account_id="acct_javier_biz",
                device_id="dev_rowhouse_hub",
                merchant_id="merch_remitline",
                occurred_at=_dt("2026-03-11T08:45:00"),
                amount=3200.0,
                currency="USD",
                channel=TransactionChannel.BANK_TRANSFER,
                status=TransactionStatus.REVIEW,
            ),
            TransactionRecord(
                transaction_id="txn_3002",
                customer_id="cust_javier",
                account_id="acct_javier_biz",
                device_id="dev_rowhouse_hub",
                merchant_id="merch_remitline",
                occurred_at=_dt("2026-03-11T08:49:00"),
                amount=3150.0,
                currency="USD",
                channel=TransactionChannel.BANK_TRANSFER,
                status=TransactionStatus.REVIEW,
            ),
            TransactionRecord(
                transaction_id="txn_3003",
                customer_id="cust_marisol",
                account_id="acct_marisol",
                device_id="dev_rowhouse_hub",
                merchant_id="merch_coinstack",
                occurred_at=_dt("2026-03-11T09:12:00"),
                amount=980.0,
                currency="USD",
                channel=TransactionChannel.WALLET,
                status=TransactionStatus.APPROVED,
            ),
            TransactionRecord(
                transaction_id="txn_3004",
                customer_id="cust_terrence",
                account_id="acct_terrence",
                device_id="dev_cafe_proxy",
                merchant_id="merch_coinstack",
                occurred_at=_dt("2026-03-11T09:17:00"),
                amount=1020.0,
                currency="USD",
                channel=TransactionChannel.WALLET,
                status=TransactionStatus.REVIEW,
            ),
        ],
        investigator_notes=[
            InvestigatorNote(
                note_id="note_4001",
                subject_customer_id="cust_javier",
                author="aml.ops@bank.example",
                created_at=_dt("2026-03-11T09:25:00"),
                body=(
                    "Business account is showing outbound transfer velocity "
                    "inconsistent with payroll. "
                    "Multiple linked beneficiaries are logging in from the same home device."
                ),
            ),
            InvestigatorNote(
                note_id="note_4002",
                subject_customer_id="cust_terrence",
                author="fraud.queue@bank.example",
                created_at=_dt("2026-03-11T09:31:00"),
                body=(
                    "Cash out pattern escalated after a credential reset. Possible "
                    "money mule activity "
                    "with cross-border payout and crypto conversion."
                ),
            ),
        ],
    )

    return synthetic_identity_ring, account_takeover, payroll_mule_funnel
