from __future__ import annotations

from relational_fraud_intelligence.domain.models import (
    AnalysisExplanation,
    AnalysisResult,
    Dataset,
    ExplanationAudience,
    ExplanationProviderSummary,
    RiskLevel,
)


class DeterministicAnalysisExplanationService:
    def explain(
        self,
        *,
        dataset: Dataset,
        analysis: AnalysisResult,
        audience: ExplanationAudience,
    ) -> AnalysisExplanation:
        evidence = _build_deterministic_evidence(analysis)
        recommended_actions = _build_recommended_actions(analysis, audience)
        watchouts = _build_watchouts(analysis, audience)

        return AnalysisExplanation(
            dataset_id=dataset.dataset_id,
            dataset_name=dataset.name,
            audience=audience,
            headline=_build_headline(dataset.name, analysis),
            narrative=_build_narrative(dataset.name, analysis, audience),
            deterministic_evidence=evidence,
            recommended_actions=recommended_actions,
            watchouts=watchouts,
            provider_summary=ExplanationProviderSummary(
                requested_provider="deterministic",
                active_provider="deterministic",
                source_of_truth="statistical-and-behavioral-analysis",
                notes=[
                    "This brief is generated from the dataset's statistical and "
                    "behavioral scoring outputs.",
                    "The explanation layer does not modify scores, alerts, or case thresholds.",
                ],
            ),
        )


def _build_headline(dataset_name: str, analysis: AnalysisResult) -> str:
    if analysis.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return f"{dataset_name} is a high-priority review candidate at {analysis.risk_score}/100."
    if analysis.risk_level == RiskLevel.MEDIUM:
        return (
            f"{dataset_name} needs analyst review because the statistical and behavioral signals "
            f"reached {analysis.risk_score}/100."
        )
    return f"{dataset_name} completed analysis with a low risk score of {analysis.risk_score}/100."


def _build_narrative(
    dataset_name: str,
    analysis: AnalysisResult,
    audience: ExplanationAudience,
) -> str:
    anomaly_summary = (
        f"The system analyzed {analysis.total_transactions} transactions and found "
        f"{analysis.total_anomalies} anomaly flags."
    )
    behavioral_summary = (
        f" It also produced {len(analysis.behavioral_insights)} higher-level behavioral "
        "inference(s) from account, merchant, device, and geography structure."
        if analysis.behavioral_insights
        else ""
    )
    lead_summary = (
        f" The system synthesized {len(analysis.investigation_leads)} investigation lead(s) "
        "to turn raw findings into case-ready hypotheses."
        if analysis.investigation_leads
        else ""
    )
    if audience == ExplanationAudience.ADMIN:
        return (
            f"{dataset_name} moved through the dataset analysis workflow without relying "
            f"on an LLM for scoring. {anomaly_summary}{behavioral_summary}{lead_summary}"
            " The resulting score is "
            f"{analysis.risk_score}/100, which should drive alert and case workload decisions."
        )
    return (
        f"{dataset_name} was scored from dataset-derived statistical and behavioral inference. "
        f"{anomaly_summary}{behavioral_summary}{lead_summary} "
        f"Use the strongest anomaly evidence below to decide whether to acknowledge alerts, "
        f"open a case, or close the review as low priority."
    )


def _build_deterministic_evidence(analysis: AnalysisResult) -> list[str]:
    evidence = [
        f"Risk score: {analysis.risk_score}/100 from statistical anomaly "
        "weights, density, and relationship structure.",
        (
            f"Total anomalies: {analysis.total_anomalies} across "
            f"{analysis.total_transactions} transactions."
        ),
    ]
    if analysis.benford_is_suspicious:
        evidence.append(
            "Benford's Law deviated materially from expected leading-digit frequencies."
        )
    if analysis.outlier_count:
        evidence.append(
            "Statistical outliers flagged: "
            f"{analysis.outlier_count} ({analysis.outlier_pct}% of transactions)."
        )
    if analysis.velocity_spikes:
        evidence.append(f"Velocity spikes detected: {len(analysis.velocity_spikes)}.")
    if analysis.behavioral_insights:
        evidence.append(
            f"Behavioral inferences: {len(analysis.behavioral_insights)} "
            "higher-level account, merchant, or device findings."
        )
        evidence.append(analysis.behavioral_insights[0].narrative)
    if analysis.investigation_leads:
        evidence.append(
            f"Investigation leads: {len(analysis.investigation_leads)} case-ready hypotheses."
        )
        evidence.append(
            f"Top lead: {analysis.investigation_leads[0].title}. "
            f"{analysis.investigation_leads[0].hypothesis}"
        )
    if analysis.graph_analysis is not None:
        evidence.append(
            "Relationship graph amplification: "
            f"{analysis.graph_analysis.risk_amplification_factor:.2f}x."
        )

    round_amounts = sum(
        1 for anomaly in analysis.anomalies if anomaly.anomaly_type == "round-amount"
    )
    if round_amounts:
        evidence.append(f"Round-amount structuring flags detected: {round_amounts}.")
    return evidence


def _build_recommended_actions(
    analysis: AnalysisResult,
    audience: ExplanationAudience,
) -> list[str]:
    actions: list[str] = []
    if analysis.investigation_leads:
        for action in analysis.investigation_leads[0].recommended_actions:
            if action not in actions:
                actions.append(action)
    if analysis.risk_score >= 35:
        actions.append("Review the generated alerts before they fall behind the queue.")
    if analysis.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        actions.append("Open or update a case so the evidence trail stays attached to the dataset.")
    if analysis.velocity_spikes:
        actions.append(
            "Inspect the spike windows and identify the accounts or merchants driving them."
        )
    if analysis.behavioral_insights:
        actions.append(
            "Validate the highest-signal behavioral inference and confirm "
            "whether the linked entities belong in the same case."
        )
    if analysis.outlier_count:
        actions.append(
            "Sample the highest-value outliers to confirm whether the activity is legitimate."
        )
    if analysis.benford_is_suspicious:
        actions.append(
            "Validate whether the amount distribution suggests fabricated or structured inputs."
        )
    if audience == ExplanationAudience.ADMIN:
        actions.append(
            "Use the dashboard and audit trail to confirm the queue is moving after triage."
        )
    return actions[:4]


def _build_watchouts(
    analysis: AnalysisResult,
    audience: ExplanationAudience,
) -> list[str]:
    watchouts = [
        "The explanation layer is advisory. Statistical and behavioral "
        "scoring remain the source of truth.",
    ]
    if analysis.investigation_leads:
        watchouts.append(
            "Investigation leads are hypotheses assembled from the dataset, not "
            "confirmed fraud outcomes."
        )
    if analysis.total_anomalies == 0:
        watchouts.append(
            "No anomaly evidence was detected, so alerts and cases should remain limited."
        )
    if analysis.risk_score < 35:
        watchouts.append("This score is below the alert auto-generation threshold.")
    if audience == ExplanationAudience.ADMIN:
        watchouts.append(
            "Reference scenarios are secondary validation tools, not the primary workflow."
        )
    return watchouts[:3]
