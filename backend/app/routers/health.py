from fastapi import APIRouter

from app.schemas.common import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> HealthStatus:
    # Liveness only — never touches the database, so Lambda cold starts and
    # health checks stay green while the database is paused or unreachable.
    return HealthStatus()
