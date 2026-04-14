"""Build a richer RelationalAI semantic fraud model for showcase scenarios."""

from __future__ import annotations

from typing import Any

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
)
from relational_fraud_intelligence.domain.models import (
    RelationalAIQueryBlueprint,
    RelationalAISemanticModelSummary,
)
from relational_fraud_intelligence.infrastructure.reasoners.relationalai_sdk import (
    Config,
    Model,
    Number,
    String,
)


def build_semantic_model_summary(
    command: ReasonAboutRiskCommand,
    *,
    external_config_enabled: bool,
) -> RelationalAISemanticModelSummary:
    model = Model(
        name="fraud-semantics",
        config=Config(
            connections={"local": {"type": "duckdb", "path": ":memory:"}},
            default_connection="local",
            install_mode=False,
        ),
    )

    concept_names = [
        "Customer",
        "Account",
        "Device",
        "Merchant",
        "Transaction",
        "SharedLowTrustCustomer",
        "CrossBorderCustomer",
        "ReviewPressureAccount",
        "HighValueTransaction",
    ]
    relationship_names = [
        "customer_owns_account",
        "customer_uses_device",
        "customer_transacts_with_merchant",
        "account_routes_payment_to_merchant",
        "customer_performed_transaction",
        "transaction_used_device",
        "transaction_settled_at_merchant",
    ]
    derived_rule_names = [
        "shared-low-trust-device-exposure",
        "cross-border-merchant-exposure",
        "review-pressure-account",
        "high-value-transaction",
    ]

    Customer = model.Concept("Customer", identify_by={"customer_id": String})
    Account = model.Concept("Account", identify_by={"account_id": String})
    Device = model.Concept("Device", identify_by={"device_id": String})
    Merchant = model.Concept("Merchant", identify_by={"merchant_id": String})
    Transaction = model.Concept("Transaction", identify_by={"transaction_id": String})

    Customer.country_code = model.Property(f"{Customer} is in {String:country_code}")
    Customer.segment = model.Property(f"{Customer} has segment {String:segment}")
    Customer.linked_account_count = model.Property(
        f"{Customer} has linked account count {Number:linked_account_count}"
    )
    Customer.linked_device_count = model.Property(
        f"{Customer} has linked device count {Number:linked_device_count}"
    )

    Account.current_balance = model.Property(
        f"{Account} has current balance {Number:current_balance}"
    )
    Account.average_monthly_inflow = model.Property(
        f"{Account} has monthly inflow {Number:average_monthly_inflow}"
    )
    Account.chargeback_count = model.Property(
        f"{Account} has chargeback count {Number:chargeback_count}"
    )
    Account.manual_review_count = model.Property(
        f"{Account} has manual review count {Number:manual_review_count}"
    )

    Device.ip_country_code = model.Property(
        f"{Device} resolves to country {String:ip_country_code}"
    )
    Device.linked_customer_count = model.Property(
        f"{Device} has linked customer count {Number:linked_customer_count}"
    )
    Device.trust_score = model.Property(f"{Device} has trust score {Number:trust_score}")

    Merchant.country_code = model.Property(
        f"{Merchant} operates in {String:country_code}"
    )
    Merchant.category = model.Property(f"{Merchant} has category {String:category}")

    Transaction.amount = model.Property(f"{Transaction} has amount {Number:amount}")
    Transaction.currency = model.Property(f"{Transaction} has currency {String:currency}")
    Transaction.channel = model.Property(f"{Transaction} has channel {String:channel}")
    Transaction.status = model.Property(f"{Transaction} has status {String:status}")

    CustomerOwnsAccount = model.Relationship(
        f"{Customer:customer} owns {Account:account}"
    )
    CustomerUsesDevice = model.Relationship(f"{Customer:customer} uses {Device:device}")
    CustomerTransactsWithMerchant = model.Relationship(
        f"{Customer:customer} transacts with {Merchant:merchant}"
    )
    AccountRoutesPaymentToMerchant = model.Relationship(
        f"{Account:account} routes payment to {Merchant:merchant}"
    )
    CustomerPerformedTransaction = model.Relationship(
        f"{Customer:customer} performed {Transaction:transaction}"
    )
    TransactionUsedDevice = model.Relationship(
        f"{Transaction:transaction} used {Device:device}"
    )
    TransactionSettledAtMerchant = model.Relationship(
        f"{Transaction:transaction} settled at {Merchant:merchant}"
    )

    SharedLowTrustCustomer = model.Concept(
        "SharedLowTrustCustomer", extends=[Customer]
    )
    CrossBorderCustomer = model.Concept("CrossBorderCustomer", extends=[Customer])
    ReviewPressureAccount = model.Concept(
        "ReviewPressureAccount", extends=[Account]
    )
    HighValueTransaction = model.Concept(
        "HighValueTransaction", extends=[Transaction]
    )

    definitions: list[Any] = []

    for customer in command.scenario.customers:
        definitions.append(
            Customer.new(
                customer_id=customer.customer_id,
                country_code=customer.country_code,
                segment=customer.segment,
                linked_account_count=len(customer.linked_account_ids),
                linked_device_count=len(customer.linked_device_ids),
            )
        )

    for account in command.scenario.accounts:
        definitions.append(
            Account.new(
                account_id=account.account_id,
                current_balance=account.current_balance,
                average_monthly_inflow=account.average_monthly_inflow,
                chargeback_count=account.chargeback_count,
                manual_review_count=account.manual_review_count,
            )
        )
        definitions.append(
            CustomerOwnsAccount(
                Customer.new(customer_id=account.customer_id),
                Account.new(account_id=account.account_id),
            )
        )

    for device in command.scenario.devices:
        definitions.append(
            Device.new(
                device_id=device.device_id,
                ip_country_code=device.ip_country_code,
                linked_customer_count=len(device.linked_customer_ids),
                trust_score=device.trust_score,
            )
        )
        for customer_id in device.linked_customer_ids:
            definitions.append(
                CustomerUsesDevice(
                    Customer.new(customer_id=customer_id),
                    Device.new(device_id=device.device_id),
                )
            )

    for merchant in command.scenario.merchants:
        definitions.append(
            Merchant.new(
                merchant_id=merchant.merchant_id,
                country_code=merchant.country_code,
                category=merchant.category,
            )
        )

    for transaction in command.scenario.transactions:
        definitions.append(
            Transaction.new(
                transaction_id=transaction.transaction_id,
                amount=transaction.amount,
                currency=transaction.currency,
                channel=transaction.channel.value,
                status=transaction.status.value,
            )
        )
        definitions.extend(
            [
                CustomerPerformedTransaction(
                    Customer.new(customer_id=transaction.customer_id),
                    Transaction.new(transaction_id=transaction.transaction_id),
                ),
                TransactionUsedDevice(
                    Transaction.new(transaction_id=transaction.transaction_id),
                    Device.new(device_id=transaction.device_id),
                ),
                TransactionSettledAtMerchant(
                    Transaction.new(transaction_id=transaction.transaction_id),
                    Merchant.new(merchant_id=transaction.merchant_id),
                ),
                CustomerTransactsWithMerchant(
                    Customer.new(customer_id=transaction.customer_id),
                    Merchant.new(merchant_id=transaction.merchant_id),
                ),
                AccountRoutesPaymentToMerchant(
                    Account.new(account_id=transaction.account_id),
                    Merchant.new(merchant_id=transaction.merchant_id),
                ),
            ]
        )

    if definitions:
        model.define(*definitions)

    model.where(
        CustomerUsesDevice.customer,
        CustomerUsesDevice.device,
        Device.linked_customer_count > 1,
        Device.trust_score < 0.5,
    ).define(SharedLowTrustCustomer(CustomerUsesDevice.customer))
    model.where(
        CustomerTransactsWithMerchant.customer.country_code
        != CustomerTransactsWithMerchant.merchant.country_code
    ).define(CrossBorderCustomer(CustomerTransactsWithMerchant.customer))
    model.where(
        (Account.chargeback_count > 0) | (Account.manual_review_count > 0)
    ).define(ReviewPressureAccount(Account))
    model.where(Transaction.amount >= 2500).define(
        HighValueTransaction(Transaction)
    )

    compiled_model = model.to_metamodel()
    query_blueprints = [
        RelationalAIQueryBlueprint(
            code="shared-low-trust-devices",
            description=(
                "Find customers connected through low-trust devices with fan-out "
                "to multiple identities."
            ),
        ),
        RelationalAIQueryBlueprint(
            code="cross-border-merchant-exposure",
            description=(
                "Trace customers whose merchant exposure crosses borders and overlaps "
                "with shared infrastructure."
            ),
        ),
        RelationalAIQueryBlueprint(
            code="merchant-fan-in-hubs",
            description=(
                "Surface merchants that attract disproportionate payment fan-in from "
                "connected accounts."
            ),
        ),
        RelationalAIQueryBlueprint(
            code="review-pressure-accounts",
            description=(
                "Blend account review pressure with device sharing and transaction "
                "intensity."
            ),
        ),
    ]

    execution_posture = (
        "External RelationalAI config is enabled for projection, while the local "
        "showcase compiles the semantic fraud model into a metamodel before "
        "remote execution."
        if external_config_enabled
        else "Local showcase mode compiles the semantic fraud model into a "
        "RelationalAI metamodel without requiring remote query execution."
    )

    return RelationalAISemanticModelSummary(
        concept_names=concept_names,
        relationship_names=relationship_names,
        derived_rule_names=derived_rule_names,
        query_blueprints=query_blueprints,
        seeded_fact_count=len(definitions),
        compiled_type_count=len(compiled_model.types),
        compiled_relation_count=len(compiled_model.relations),
        execution_posture=execution_posture,
    )
