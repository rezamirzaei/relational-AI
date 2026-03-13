from relational_fraud_intelligence.domain.models import AppModel, DashboardStats, WorkspaceGuide


class GetDashboardStatsQuery(AppModel):
    pass


class GetDashboardStatsResult(AppModel):
    stats: DashboardStats


class GetWorkspaceGuideResult(AppModel):
    guide: WorkspaceGuide
