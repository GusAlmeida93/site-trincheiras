from fastapi import APIRouter

from app.schemas.common import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> HealthStatus:
    # Liveness only — never touches the database, so Cloud Run / ALB health
    # checks stay green through transient DB outages.
    return HealthStatus()
