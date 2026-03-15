"""API route assembler — includes all sub-routers."""

from fastapi import APIRouter

from relational_fraud_intelligence.api.alert_routes import router as alert_router
from relational_fraud_intelligence.api.auth_routes import router as auth_router
from relational_fraud_intelligence.api.case_routes import router as case_router
from relational_fraud_intelligence.api.dashboard_routes import router as dashboard_router
from relational_fraud_intelligence.api.dataset_routes import router as dataset_router
from relational_fraud_intelligence.api.health_routes import router as health_router
from relational_fraud_intelligence.api.investigation_routes import router as investigation_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(investigation_router)
router.include_router(case_router)
router.include_router(alert_router)
router.include_router(dashboard_router)
router.include_router(dataset_router)
