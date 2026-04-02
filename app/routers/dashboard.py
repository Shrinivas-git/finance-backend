from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rbac import get_current_user, require_analyst_or_above
from app.models.user import User
from app.schemas.dashboard import AnalystInsights, DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get financial summary [All roles]",
)
def get_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return dashboard_service.get_dashboard_summary(db)


@router.get(
    "/insights",
    response_model=AnalystInsights,
    summary="Get advanced financial insights [Analyst and Admin only]",
)
def get_insights(
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst_or_above),
):
    """
    Returns deeper analytical data:
    - Average transaction amount
    - Average monthly income / expense
    - Top 5 income and expense categories with percentage share
    - Weekly trends (ISO week)
    - Highest single income and expense
    """
    return dashboard_service.get_analyst_insights(db)
