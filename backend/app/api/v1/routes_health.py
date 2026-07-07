"""Health and readiness probes.

`/health` is a cheap liveness check (process is up). `/ready` is a readiness
check that verifies critical dependencies (database, broker) are reachable, so an
orchestrator only routes traffic when the service can actually serve requests.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.database.session import check_database
from app.workers.celery_app import check_broker

router = APIRouter(tags=["health"])
log = get_logger(__name__)


# Accept HEAD as well as GET so uptime monitors (UptimeRobot defaults to HEAD)
# don't get a 405 when pinging the liveness probe.
@router.api_route("/health", methods=["GET", "HEAD"], summary="Liveness probe")
def health() -> dict[str, str]:
    """Return 200 while the process is alive. No dependency checks."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
def ready() -> JSONResponse:
    """Return 200 only when the database and broker are both reachable."""
    checks = {"database": check_database(), "broker": check_broker()}
    healthy = all(checks.values())
    code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    if not healthy:
        log.warning("readiness_check_failed", checks=checks)
    return JSONResponse(status_code=code, content={"ready": healthy, "checks": checks})
