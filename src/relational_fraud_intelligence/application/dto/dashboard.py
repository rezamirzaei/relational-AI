from relational_fraud_intelligence.domain.models import AppModel, DashboardStats


class GetDashboardStatsQuery(AppModel):
    pass


class GetDashboardStatsResult(AppModel):
    stats: DashboardStats
