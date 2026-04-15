"""Build a richer RelationalAI semantic fraud model for showcase scenarios."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
)
from relational_fraud_intelligence.domain.models import (
    EntityReference,
    EntityType,
    GraphLink,
    RelationalAIQueryBlueprint,
    RelationalAISemanticFinding,
    RelationalAISemanticModelSummary,
    ScenarioTag,
)
from relational_fraud_intelligence.infrastructure.reasoners.relationalai_sdk import (
    Config,
    Model,
    Number,
    String,
    create_config,
)


@dataclass(frozen=True, slots=True)
class _SemanticHandles:
    Account: Any
    CrossBorderCustomer: Any
    HighValueTransaction: Any
    InvestigatorAssertion: Any
    LiquidationMerchant: Any
    RapidWindowTransaction: Any
    RecentAccount: Any
    ReviewPressureAccount: Any
    SharedLowTrustCustomer: Any
    Transaction: Any


def build_semantic_model_summary(
    command: ReasonAboutRiskCommand,
    *,
    external_config_enabled: bool,
    model_config: Any | None = None,
) -> RelationalAISemanticModelSummary:
    config = model_config or (
        create_config()
        if external_config_enabled
        else Config(
            connections={"local": {"type": "duckdb", "path": ":memory:"}},
            default_connection="local",
            install_mode=False,
        )
    )
    model = Model(
        name="fraud-semantics",
        config=config,
    )

    active_rule_packs = _active_rule_packs(command)
    concept_names = [
        "Customer",
        "Account",
        "Device",
        "Merchant",
        "Transaction",
        "InvestigatorAssertion",
        "SharedLowTrustCustomer",
        "CrossBorderCustomer",
        "ReviewPressureAccount",
        "HighValueTransaction",
        "RecentAccount",
        "LiquidationMerchant",
        "RapidWindowTransaction",
    ]
    relationship_names = [
        "customer_owns_account",
        "customer_uses_device",
        "customer_transacts_with_merchant",
        "account_routes_payment_to_merchant",
        "customer_performed_transaction",
        "transaction_used_device",
        "transaction_settled_at_merchant",
        "assertion_supports_customer",
    ]
    derived_rule_names = [
        "shared-low-trust-device-exposure",
        "cross-border-merchant-exposure",
        "review-pressure-account",
        "high-value-transaction",
        "recent-account-pressure",
        "merchant-liquidation-archetype",
        "investigator-feedback-loop",
        "rapid-high-value-window",
    ]

    Customer = model.Concept("Customer", identify_by={"customer_id": String})
    Account = model.Concept("Account", identify_by={"account_id": String})
    Device = model.Concept("Device", identify_by={"device_id": String})
    Merchant = model.Concept("Merchant", identify_by={"merchant_id": String})
    Transaction = model.Concept("Transaction", identify_by={"transaction_id": String})
    InvestigatorAssertion = model.Concept(
        "InvestigatorAssertion",
        identify_by={"note_id": String},
    )

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

    InvestigatorAssertion.author = model.Property(
        f"{InvestigatorAssertion} has author {String:author}"
    )
    InvestigatorAssertion.body = model.Property(
        f"{InvestigatorAssertion} has body {String:body}"
    )

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
    AssertionSupportsCustomer = model.Relationship(
        f"{InvestigatorAssertion:assertion} supports {Customer:customer}"
    )

    SharedLowTrustCustomer = model.Concept(
        "SharedLowTrustCustomer",
        extends=[Customer],
    )
    CrossBorderCustomer = model.Concept("CrossBorderCustomer", extends=[Customer])
    ReviewPressureAccount = model.Concept(
        "ReviewPressureAccount",
        extends=[Account],
    )
    HighValueTransaction = model.Concept(
        "HighValueTransaction",
        extends=[Transaction],
    )
    RecentAccount = model.Concept("RecentAccount", extends=[Account])
    LiquidationMerchant = model.Concept("LiquidationMerchant", extends=[Merchant])
    RapidWindowTransaction = model.Concept(
        "RapidWindowTransaction",
        extends=[Transaction],
    )
    handles = _SemanticHandles(
        Account=Account,
        CrossBorderCustomer=CrossBorderCustomer,
        HighValueTransaction=HighValueTransaction,
        InvestigatorAssertion=InvestigatorAssertion,
        LiquidationMerchant=LiquidationMerchant,
        RapidWindowTransaction=RapidWindowTransaction,
        RecentAccount=RecentAccount,
        ReviewPressureAccount=ReviewPressureAccount,
        SharedLowTrustCustomer=SharedLowTrustCustomer,
        Transaction=Transaction,
    )

    definitions: list[Any] = []
    device_lookup = {device.device_id: device for device in command.scenario.devices}
    account_lookup = {account.account_id: account for account in command.scenario.accounts}
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

        account_profile = account_lookup.get(transaction.account_id)
        if account_profile is not None and (
            transaction.occurred_at - account_profile.opened_at
        ).days <= 30:
            definitions.append(
                RecentAccount(Account.new(account_id=account_profile.account_id))
            )

        device_profile = device_lookup.get(transaction.device_id)
        if transaction.amount >= 2500:
            definitions.append(
                HighValueTransaction(
                    Transaction.new(transaction_id=transaction.transaction_id)
                )
            )
        if (
            device_profile is not None
            and device_profile.trust_score < 0.5
            and transaction.amount >= 1500
        ):
            definitions.append(
                RapidWindowTransaction(
                    Transaction.new(transaction_id=transaction.transaction_id)
                )
            )

    for merchant in command.scenario.merchants:
        if _is_liquidation_merchant(merchant.category, merchant.description):
            definitions.append(
                LiquidationMerchant(Merchant.new(merchant_id=merchant.merchant_id))
            )

    for note in command.scenario.investigator_notes:
        definitions.append(
            InvestigatorAssertion.new(
                note_id=note.note_id,
                author=note.author,
                body=note.body,
            )
        )
        definitions.append(
            AssertionSupportsCustomer(
                InvestigatorAssertion.new(note_id=note.note_id),
                Customer.new(customer_id=note.subject_customer_id),
            )
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

    compiled_model = model.to_metamodel()
    query_blueprints = _query_blueprints(active_rule_packs)
    findings = _semantic_findings(
        command,
        active_rule_packs=active_rule_packs,
        external_config_enabled=external_config_enabled,
    )
    if external_config_enabled:
        findings = _augment_findings_with_external_queries(
            model=model,
            handles=handles,
            findings=findings,
        )

    execution_posture = (
        "External RelationalAI config is enabled for projection and semantic query "
        "execution. Typed findings are promoted from compiled rule packs and then "
        "checked against executed RelationalAI concept queries."
        if external_config_enabled
        else "Local showcase mode compiles the semantic fraud model into a "
        "RelationalAI metamodel and promotes rule-pack findings without requiring "
        "remote query execution."
    )

    return RelationalAISemanticModelSummary(
        concept_names=concept_names,
        relationship_names=relationship_names,
        derived_rule_names=derived_rule_names,
        query_blueprints=query_blueprints,
        active_rule_packs=active_rule_packs,
        semantic_findings=findings,
        seeded_fact_count=len(definitions),
        compiled_type_count=len(compiled_model.types),
        compiled_relation_count=len(compiled_model.relations),
        execution_posture=execution_posture,
    )


def _active_rule_packs(command: ReasonAboutRiskCommand) -> list[str]:
    tags = set(command.scenario.tags)
    rule_packs = {
        "shared-infrastructure",
        "merchant-archetypes",
        "temporal-windows",
    }
    if {
        ScenarioTag.CROSS_BORDER,
        ScenarioTag.MONEY_MULE,
    } & tags:
        rule_packs.add("cross-border-corridors")
    if {
        ScenarioTag.BUST_OUT,
        ScenarioTag.FIRST_PARTY,
    } & tags:
        rule_packs.add("account-lifecycle")
    if ScenarioTag.ACCOUNT_TAKEOVER in tags:
        rule_packs.add("account-takeover")
    if {
        ScenarioTag.SYNTHETIC_IDENTITY,
        ScenarioTag.DEVICE_RING,
    } & tags:
        rule_packs.add("identity-ring")
    if command.scenario.investigator_notes or command.text_signals:
        rule_packs.add("investigator-feedback")
    return sorted(rule_packs)


def _query_blueprints(active_rule_packs: list[str]) -> list[RelationalAIQueryBlueprint]:
    blueprints = [
        RelationalAIQueryBlueprint(
            code="shared-low-trust-devices",
            description=(
                "Find customers connected through low-trust devices with fan-out "
                "to multiple identities."
            ),
            rule_pack="shared-infrastructure",
            derived_rule_paths=[
                "customer_uses_device",
                "Device.trust_score < 0.5",
                "SharedLowTrustCustomer",
            ],
        ),
        RelationalAIQueryBlueprint(
            code="cross-border-merchant-exposure",
            description=(
                "Trace customers whose merchant exposure crosses borders and overlaps "
                "with shared infrastructure."
            ),
            rule_pack="cross-border-corridors",
            derived_rule_paths=[
                "customer_transacts_with_merchant",
                "Customer.country_code != Merchant.country_code",
                "CrossBorderCustomer",
            ],
        ),
        RelationalAIQueryBlueprint(
            code="merchant-liquidation-archetypes",
            description=(
                "Surface merchants whose category and transaction behavior fit a "
                "rapid liquidation or transfer archetype."
            ),
            rule_pack="merchant-archetypes",
            derived_rule_paths=[
                "transaction_settled_at_merchant",
                "LiquidationMerchant",
            ],
        ),
        RelationalAIQueryBlueprint(
            code="review-pressure-accounts",
            description=(
                "Blend account review pressure with device sharing and transaction "
                "intensity."
            ),
            rule_pack="account-lifecycle",
            derived_rule_paths=[
                "customer_owns_account",
                "ReviewPressureAccount",
            ],
        ),
        RelationalAIQueryBlueprint(
            code="rapid-high-value-windows",
            description=(
                "Identify compact time windows where the same actor pushes multiple "
                "high-value transactions through shared rails."
            ),
            rule_pack="temporal-windows",
            derived_rule_paths=[
                "customer_performed_transaction",
                "RapidWindowTransaction",
                "HighValueTransaction",
            ],
        ),
        RelationalAIQueryBlueprint(
            code="investigator-feedback-loop",
            description=(
                "Treat investigator assertions and text signals as semantic facts "
                "that reinforce or challenge the network story."
            ),
            rule_pack="investigator-feedback",
            derived_rule_paths=[
                "assertion_supports_customer",
                "InvestigatorAssertion",
            ],
        ),
    ]
    active = set(active_rule_packs)
    return [blueprint for blueprint in blueprints if blueprint.rule_pack in active]


def _semantic_findings(
    command: ReasonAboutRiskCommand,
    *,
    active_rule_packs: list[str],
    external_config_enabled: bool,
) -> list[RelationalAISemanticFinding]:
    findings: list[RelationalAISemanticFinding] = []
    execution_mode = (
        "external-config-ready" if external_config_enabled else "semantic-compiled"
    )

    findings.extend(_shared_device_findings(command, execution_mode))
    findings.extend(_cross_border_findings(command, execution_mode))
    findings.extend(_merchant_archetype_findings(command, execution_mode))
    findings.extend(_review_pressure_findings(command, execution_mode))
    findings.extend(_temporal_window_findings(command, execution_mode))
    findings.extend(_recent_account_findings(command, execution_mode))
    findings.extend(_investigator_feedback_findings(command, execution_mode))

    active = set(active_rule_packs)
    return [
        finding for finding in findings if finding.rule_pack in active
    ]


def _augment_findings_with_external_queries(
    *,
    model: Model,
    handles: _SemanticHandles,
    findings: list[RelationalAISemanticFinding],
) -> list[RelationalAISemanticFinding]:
    if not findings:
        return findings

    shared_low_trust_customer_ids = _query_identifier_values(
        model.select(handles.SharedLowTrustCustomer.customer_id)
    )
    cross_border_customer_ids = _query_identifier_values(
        model.select(handles.CrossBorderCustomer.customer_id)
    )
    review_pressure_account_ids = _query_identifier_values(
        model.select(handles.ReviewPressureAccount.account_id)
    )
    recent_account_ids = _query_identifier_values(
        model.select(handles.RecentAccount.account_id)
    )
    high_value_transaction_ids = _query_identifier_values(
        model.select(handles.HighValueTransaction.transaction_id)
    )
    rapid_window_transaction_ids = _query_identifier_values(
        model.select(handles.RapidWindowTransaction.transaction_id)
    )
    liquidation_merchant_ids = _query_identifier_values(
        model.select(handles.LiquidationMerchant.merchant_id)
    )
    investigator_assertion_ids = _query_identifier_values(
        model.select(handles.InvestigatorAssertion.note_id)
    )
    transaction_amounts = _query_two_column_mapping(
        model.select(handles.Transaction.transaction_id, handles.Transaction.amount)
    )

    augmented_findings: list[RelationalAISemanticFinding] = []
    for finding in findings:
        confirmed_anchor_ids = _confirmed_anchor_ids(
            finding,
            shared_low_trust_customer_ids=shared_low_trust_customer_ids,
            cross_border_customer_ids=cross_border_customer_ids,
            review_pressure_account_ids=review_pressure_account_ids,
            recent_account_ids=recent_account_ids,
            high_value_transaction_ids=high_value_transaction_ids,
            rapid_window_transaction_ids=rapid_window_transaction_ids,
            liquidation_merchant_ids=liquidation_merchant_ids,
            investigator_assertion_ids=investigator_assertion_ids,
        )
        supporting_volume = round(
            sum(
                transaction_amounts.get(transaction_id, 0.0)
                for transaction_id in finding.supporting_transaction_ids
            ),
            2,
        )
        if confirmed_anchor_ids:
            confirmation_note = (
                "External RelationalAI query confirmed "
                f"{len(confirmed_anchor_ids)} semantic anchor(s)"
            )
            if supporting_volume > 0:
                confirmation_note += (
                    f" across ${supporting_volume:,.2f} of supporting transaction volume"
                )
            augmented_findings.append(
                finding.model_copy(
                    update={
                        "execution_mode": "external-query-augmented",
                        "narrative": _append_sentence(
                            finding.narrative,
                            f"{confirmation_note}.",
                        ),
                        "confidence": min(
                            0.99,
                            finding.confidence + 0.06,
                        ),
                        "risk_contribution": min(
                            10,
                            finding.risk_contribution + 1,
                        ),
                    }
                )
            )
            continue
        augmented_findings.append(
            finding.model_copy(update={"execution_mode": "external-query-executed"})
        )
    return augmented_findings


def _confirmed_anchor_ids(
    finding: RelationalAISemanticFinding,
    *,
    shared_low_trust_customer_ids: set[str],
    cross_border_customer_ids: set[str],
    review_pressure_account_ids: set[str],
    recent_account_ids: set[str],
    high_value_transaction_ids: set[str],
    rapid_window_transaction_ids: set[str],
    liquidation_merchant_ids: set[str],
    investigator_assertion_ids: set[str],
) -> set[str]:
    if finding.blueprint_code == "shared-low-trust-devices":
        return _entity_ids(finding, EntityType.CUSTOMER) & shared_low_trust_customer_ids
    if finding.blueprint_code == "cross-border-merchant-exposure":
        return _entity_ids(finding, EntityType.CUSTOMER) & cross_border_customer_ids
    if finding.blueprint_code == "merchant-liquidation-archetypes":
        return _entity_ids(finding, EntityType.MERCHANT) & liquidation_merchant_ids
    if finding.blueprint_code == "review-pressure-accounts":
        return _entity_ids(finding, EntityType.ACCOUNT) & (
            review_pressure_account_ids | recent_account_ids
        )
    if finding.blueprint_code == "rapid-high-value-windows":
        return set(finding.supporting_transaction_ids) & (
            high_value_transaction_ids | rapid_window_transaction_ids
        )
    if finding.blueprint_code == "investigator-feedback-loop":
        return _entity_ids(finding, EntityType.NOTE) & investigator_assertion_ids
    return set()


def _entity_ids(
    finding: RelationalAISemanticFinding,
    entity_type: EntityType,
) -> set[str]:
    return {
        entity.entity_id
        for entity in finding.matched_entities
        if entity.entity_type == entity_type
    }


def _query_identifier_values(fragment: Any) -> set[str]:
    dataframe = fragment.to_df()
    values: set[str] = set()
    for record in dataframe.to_dict(orient="records"):
        row = tuple(record.values())
        if row and row[0] is not None:
            values.add(str(row[0]))
    return values


def _query_two_column_mapping(fragment: Any) -> dict[str, float]:
    dataframe = fragment.to_df()
    values: dict[str, float] = {}
    for record in dataframe.to_dict(orient="records"):
        row = tuple(record.values())
        if len(row) < 2 or row[0] is None or row[1] is None:
            continue
        values[str(row[0])] = float(row[1])
    return values


def _shared_device_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    customers = {customer.customer_id: customer for customer in command.scenario.customers}
    findings: list[RelationalAISemanticFinding] = []
    for device in command.scenario.devices:
        linked_customers = [
            customers[customer_id]
            for customer_id in device.linked_customer_ids
            if customer_id in customers
        ]
        if device.trust_score >= 0.5 or len(linked_customers) < 2:
            continue
        supporting_txn_ids = [
            transaction.transaction_id
            for transaction in command.scenario.transactions
            if transaction.device_id == device.device_id
        ]
        findings.append(
            RelationalAISemanticFinding(
                finding_id=f"finding::shared-device::{device.device_id}",
                blueprint_code="shared-low-trust-devices",
                title=(
                    f"Low-trust shared device {device.device_id} binds "
                    f"{len(linked_customers)} customers"
                ),
                narrative=(
                    f"Device {device.device_id} has trust {device.trust_score:.2f} and is "
                    f"shared by {len(linked_customers)} customers. The semantic rule path "
                    "treats that overlap as shared-infrastructure exposure, not isolated "
                    "transaction noise."
                ),
                rule_pack="shared-infrastructure",
                derived_rule_path=[
                    "customer_uses_device",
                    "Device.trust_score < 0.5",
                    "SharedLowTrustCustomer",
                ],
                semantic_concepts=[
                    "Customer",
                    "Device",
                    "SharedLowTrustCustomer",
                ],
                matched_entities=[
                    _device_ref(device.device_id),
                    *[
                        _customer_ref(customer.customer_id, customer.full_name)
                        for customer in linked_customers
                    ],
                ],
                evidence_edges=[
                    GraphLink(
                        relation="uses-low-trust-device",
                        source=_customer_ref(customer.customer_id, customer.full_name),
                        target=_device_ref(device.device_id),
                        explanation=(
                            f"{customer.full_name} authenticated through low-trust device "
                            f"{device.device_id}."
                        ),
                    )
                    for customer in linked_customers
                ],
                supporting_transaction_ids=supporting_txn_ids,
                risk_contribution=min(8, 4 + len(linked_customers)),
                confidence=min(0.97, 0.6 + len(linked_customers) * 0.1),
                execution_mode=execution_mode,
            )
        )
    return findings


def _cross_border_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    customer_lookup = {
        customer.customer_id: customer for customer in command.scenario.customers
    }
    merchant_lookup = {
        merchant.merchant_id: merchant for merchant in command.scenario.merchants
    }
    merchant_transactions: dict[str, list[Any]] = defaultdict(list)
    for transaction in command.scenario.transactions:
        merchant_transactions[transaction.merchant_id].append(transaction)

    findings: list[RelationalAISemanticFinding] = []
    for merchant_id, transactions in merchant_transactions.items():
        merchant = merchant_lookup.get(merchant_id)
        if merchant is None:
            continue
        participating_customers = []
        cross_border_customers = []
        for transaction in transactions:
            customer = customer_lookup.get(transaction.customer_id)
            if customer is None:
                continue
            participating_customers.append(customer)
            if customer.country_code != merchant.country_code:
                cross_border_customers.append(customer)
        countries = {customer.country_code for customer in participating_customers}
        if not cross_border_customers or len(countries) < 2:
            continue
        unique_customers = {
            customer.customer_id: customer for customer in cross_border_customers
        }.values()
        findings.append(
            RelationalAISemanticFinding(
                finding_id=f"finding::cross-border::{merchant_id}",
                blueprint_code="cross-border-merchant-exposure",
                title=f"Cross-border corridor centers on {merchant.display_name}",
                narrative=(
                    f"Merchant {merchant.display_name} sits at a corridor that connects "
                    f"{len(countries)} customer geographies. The semantic rule path flags "
                    "it because customer country and merchant country diverge across "
                    "shared settlement activity."
                ),
                rule_pack="cross-border-corridors",
                derived_rule_path=[
                    "customer_transacts_with_merchant",
                    "Customer.country_code != Merchant.country_code",
                    "CrossBorderCustomer",
                ],
                semantic_concepts=[
                    "Customer",
                    "Merchant",
                    "CrossBorderCustomer",
                ],
                matched_entities=[
                    _merchant_ref(merchant.merchant_id, merchant.display_name),
                    *[
                        _customer_ref(customer.customer_id, customer.full_name)
                        for customer in unique_customers
                    ],
                ],
                evidence_edges=[
                    GraphLink(
                        relation="cross-border-exposure",
                        source=_customer_ref(customer.customer_id, customer.full_name),
                        target=_merchant_ref(merchant.merchant_id, merchant.display_name),
                        explanation=(
                            f"{customer.full_name} transacted across borders through "
                            f"{merchant.display_name}."
                        ),
                    )
                    for customer in unique_customers
                ],
                supporting_transaction_ids=[
                    transaction.transaction_id for transaction in transactions
                ],
                risk_contribution=min(9, 5 + len(countries)),
                confidence=min(0.96, 0.58 + len(countries) * 0.12),
                execution_mode=execution_mode,
            )
        )
    return findings


def _merchant_archetype_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    merchant_transactions: dict[str, list[Any]] = defaultdict(list)
    for transaction in command.scenario.transactions:
        merchant_transactions[transaction.merchant_id].append(transaction)

    findings: list[RelationalAISemanticFinding] = []
    for merchant in command.scenario.merchants:
        if not _is_liquidation_merchant(merchant.category, merchant.description):
            continue
        transactions = merchant_transactions.get(merchant.merchant_id, [])
        if not transactions:
            continue
        volume = sum(transaction.amount for transaction in transactions)
        findings.append(
            RelationalAISemanticFinding(
                finding_id=f"finding::merchant-archetype::{merchant.merchant_id}",
                blueprint_code="merchant-liquidation-archetypes",
                title=f"Merchant archetype indicates liquidation rail at {merchant.display_name}",
                narrative=(
                    f"{merchant.display_name} fits a liquidation merchant archetype "
                    f"({merchant.category}) and absorbed ${volume:,.2f} in scenario flow. "
                    "That semantic archetype helps explain why the network can cash out "
                    "quickly once accounts are compromised or funded."
                ),
                rule_pack="merchant-archetypes",
                derived_rule_path=[
                    "transaction_settled_at_merchant",
                    "LiquidationMerchant",
                ],
                semantic_concepts=[
                    "Merchant",
                    "Transaction",
                    "LiquidationMerchant",
                ],
                matched_entities=[
                    _merchant_ref(merchant.merchant_id, merchant.display_name)
                ],
                evidence_edges=[
                    GraphLink(
                        relation="settled-at-liquidation-merchant",
                        source=_transaction_ref(transaction.transaction_id),
                        target=_merchant_ref(merchant.merchant_id, merchant.display_name),
                        explanation=(
                            f"Transaction {transaction.transaction_id} settled at merchant "
                            f"{merchant.display_name}, which fits a liquidation archetype."
                        ),
                    )
                    for transaction in transactions[:4]
                ],
                supporting_transaction_ids=[
                    transaction.transaction_id for transaction in transactions
                ],
                risk_contribution=5 if volume < 5000 else 7,
                confidence=0.82 if volume < 5000 else 0.9,
                execution_mode=execution_mode,
            )
        )
    return findings


def _review_pressure_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    customer_lookup = {
        customer.customer_id: customer for customer in command.scenario.customers
    }
    findings: list[RelationalAISemanticFinding] = []
    for account in command.scenario.accounts:
        pressure = account.chargeback_count + account.manual_review_count
        if pressure <= 0:
            continue
        customer = customer_lookup.get(account.customer_id)
        matched_entities = [_account_ref(account.account_id)]
        if customer is not None:
            matched_entities.insert(
                0,
                _customer_ref(customer.customer_id, customer.full_name),
            )
        findings.append(
            RelationalAISemanticFinding(
                finding_id=f"finding::review-pressure::{account.account_id}",
                blueprint_code="review-pressure-accounts",
                title=f"Account {account.account_id} is already under review pressure",
                narrative=(
                    f"Account {account.account_id} carries {account.chargeback_count} chargeback "
                    f"signals and {account.manual_review_count} prior manual reviews. The "
                    "semantic lifecycle layer treats that pressure as cumulative evidence."
                ),
                rule_pack="account-lifecycle",
                derived_rule_path=[
                    "customer_owns_account",
                    "ReviewPressureAccount",
                ],
                semantic_concepts=[
                    "Customer",
                    "Account",
                    "ReviewPressureAccount",
                ],
                matched_entities=matched_entities,
                evidence_edges=[
                    GraphLink(
                        relation="owns-reviewed-account",
                        source=_customer_ref(customer.customer_id, customer.full_name),
                        target=_account_ref(account.account_id),
                        explanation=(
                            f"{customer.full_name} controls account {account.account_id}, "
                            "which already carries review pressure."
                        ),
                    )
                    for customer in [customer]
                    if customer is not None
                ],
                risk_contribution=min(7, 3 + pressure),
                confidence=min(0.95, 0.58 + pressure * 0.08),
                execution_mode=execution_mode,
            )
        )
    return findings


def _temporal_window_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    customer_lookup = {
        customer.customer_id: customer for customer in command.scenario.customers
    }
    grouped: dict[str, list[Any]] = defaultdict(list)
    for transaction in command.scenario.transactions:
        grouped[transaction.customer_id].append(transaction)

    findings: list[RelationalAISemanticFinding] = []
    for customer_id, transactions in grouped.items():
        ordered = sorted(transactions, key=lambda transaction: transaction.occurred_at)
        for start_index, start_transaction in enumerate(ordered):
            window = [start_transaction]
            total_amount = start_transaction.amount
            for other in ordered[start_index + 1 :]:
                minutes = (
                    other.occurred_at - start_transaction.occurred_at
                ).total_seconds() / 60
                if minutes > 15:
                    break
                window.append(other)
                total_amount += other.amount
            if len(window) < 2 or total_amount < 2500:
                continue
            customer = customer_lookup.get(customer_id)
            customer_name = customer.full_name if customer is not None else customer_id
            findings.append(
                RelationalAISemanticFinding(
                    finding_id=f"finding::rapid-window::{customer_id}",
                    blueprint_code="rapid-high-value-windows",
                    title=f"Rapid high-value window for {customer_name}",
                    narrative=(
                        f"{customer_name} pushed {len(window)} transactions totaling "
                        f"${total_amount:,.2f} within 15 minutes. The temporal semantic "
                        "window upgrades those events from isolated rows to a coordinated "
                        "burst pattern."
                    ),
                    rule_pack="temporal-windows",
                    derived_rule_path=[
                        "customer_performed_transaction",
                        "RapidWindowTransaction",
                        "HighValueTransaction",
                    ],
                    semantic_concepts=[
                        "Customer",
                        "Transaction",
                        "RapidWindowTransaction",
                    ],
                    matched_entities=[
                        _customer_ref(customer.customer_id, customer.full_name)
                        for customer in [customer]
                        if customer is not None
                    ]
                    + [_transaction_ref(transaction.transaction_id) for transaction in window],
                    evidence_edges=[
                        GraphLink(
                            relation="rapid-window-transaction",
                            source=_customer_ref(customer.customer_id, customer.full_name),
                            target=_transaction_ref(transaction.transaction_id),
                            explanation=(
                                f"{customer.full_name} initiated transaction "
                                f"{transaction.transaction_id} inside the rapid window."
                            ),
                        )
                        for customer in [customer]
                        if customer is not None
                        for transaction in window
                    ],
                    supporting_transaction_ids=[
                        transaction.transaction_id for transaction in window
                    ],
                    risk_contribution=min(8, 4 + len(window)),
                    confidence=min(0.95, 0.6 + len(window) * 0.08),
                    execution_mode=execution_mode,
                )
            )
            break
    return findings


def _recent_account_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    transactions_by_account: dict[str, list[Any]] = defaultdict(list)
    for transaction in command.scenario.transactions:
        transactions_by_account[transaction.account_id].append(transaction)

    findings: list[RelationalAISemanticFinding] = []
    for account in command.scenario.accounts:
        transactions = transactions_by_account.get(account.account_id, [])
        if not transactions:
            continue
        first_activity = min(transaction.occurred_at for transaction in transactions)
        age_days = (first_activity - account.opened_at).days
        volume = sum(transaction.amount for transaction in transactions)
        if age_days > 30 or volume < max(2000.0, account.average_monthly_inflow):
            continue
        findings.append(
            RelationalAISemanticFinding(
                finding_id=f"finding::recent-account::{account.account_id}",
                blueprint_code="review-pressure-accounts",
                title=f"Recently opened account {account.account_id} accelerated too quickly",
                narrative=(
                    f"Account {account.account_id} moved ${volume:,.2f} within {age_days} "
                    "days of opening. The lifecycle semantic layer treats that acceleration "
                    "as a bust-out or mule onboarding pressure signal."
                ),
                rule_pack="account-lifecycle",
                derived_rule_path=[
                    "customer_owns_account",
                    "RecentAccount",
                    "ReviewPressureAccount",
                ],
                semantic_concepts=[
                    "Account",
                    "RecentAccount",
                    "ReviewPressureAccount",
                ],
                matched_entities=[_account_ref(account.account_id)],
                evidence_edges=[
                    GraphLink(
                        relation="recent-account-activity",
                        source=_account_ref(account.account_id),
                        target=_transaction_ref(transaction.transaction_id),
                        explanation=(
                            f"Transaction {transaction.transaction_id} contributed to rapid "
                            f"early activity on account {account.account_id}."
                        ),
                    )
                    for transaction in transactions[:4]
                ],
                supporting_transaction_ids=[
                    transaction.transaction_id for transaction in transactions
                ],
                risk_contribution=6,
                confidence=0.84,
                execution_mode=execution_mode,
            )
        )
    return findings


def _investigator_feedback_findings(
    command: ReasonAboutRiskCommand,
    execution_mode: str,
) -> list[RelationalAISemanticFinding]:
    customer_lookup = {
        customer.customer_id: customer for customer in command.scenario.customers
    }
    findings: list[RelationalAISemanticFinding] = []
    for note in command.scenario.investigator_notes:
        customer = customer_lookup.get(note.subject_customer_id)
        if customer is None:
            continue
        findings.append(
            RelationalAISemanticFinding(
                finding_id=f"finding::investigator-note::{note.note_id}",
                blueprint_code="investigator-feedback-loop",
                title=f"Investigator assertion reinforces concern for {customer.full_name}",
                narrative=(
                    f"Analyst note {note.note_id} by {note.author} is projected as a semantic "
                    "assertion tied to the customer graph. That lets human feedback reinforce "
                    "the relational story instead of living outside it."
                ),
                rule_pack="investigator-feedback",
                derived_rule_path=[
                    "InvestigatorAssertion",
                    "assertion_supports_customer",
                ],
                semantic_concepts=[
                    "InvestigatorAssertion",
                    "Customer",
                ],
                matched_entities=[
                    _note_ref(note.note_id, note.author),
                    _customer_ref(customer.customer_id, customer.full_name),
                ],
                evidence_edges=[
                    GraphLink(
                        relation="asserts-risk-on-customer",
                        source=_note_ref(note.note_id, note.author),
                        target=_customer_ref(customer.customer_id, customer.full_name),
                        explanation=(
                            f"Investigator note {note.note_id} reinforces the case for "
                            f"{customer.full_name}."
                        ),
                    )
                ],
                risk_contribution=3,
                confidence=0.74,
                execution_mode=execution_mode,
            )
        )
    return findings


def _is_liquidation_merchant(category: str, description: str) -> bool:
    normalized = f"{category} {description}".lower()
    return any(
        token in normalized
        for token in ("digital_goods", "money_transfer", "gift", "crypto", "wire")
    )


def _append_sentence(text: str, sentence: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return sentence
    if stripped.endswith((".", "!", "?")):
        return f"{stripped} {sentence}"
    return f"{stripped}. {sentence}"


def _customer_ref(customer_id: str, display_name: str) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.CUSTOMER,
        entity_id=customer_id,
        display_name=display_name,
    )


def _account_ref(account_id: str) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.ACCOUNT,
        entity_id=account_id,
        display_name=f"Account {account_id}",
    )


def _device_ref(device_id: str) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.DEVICE,
        entity_id=device_id,
        display_name=f"Device {device_id}",
    )


def _merchant_ref(merchant_id: str, display_name: str) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.MERCHANT,
        entity_id=merchant_id,
        display_name=display_name,
    )


def _transaction_ref(transaction_id: str) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.TRANSACTION,
        entity_id=transaction_id,
        display_name=f"Transaction {transaction_id}",
    )


def _note_ref(note_id: str, author: str) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.NOTE,
        entity_id=note_id,
        display_name=f"Note {note_id} by {author}",
    )
