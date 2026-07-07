"""FastAPI application factory.

The API layer is intentionally thin: it wires middleware, routers and exception
handlers, then delegates all work to application services. No business logic lives
here. `create_app()` is a factory so tests can build isolated app instances.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import routes_health, routes_jobs
from app.config.settings import get_settings
from app.core.exceptions import (
    JobNotFoundError,
    PermanentError,
    PipelineError,
    ResultNotReadyError,
    TransientError,
)
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: configure logging on startup."""
    configure_logging()
    settings = get_settings()
    log.info("api_startup", app=settings.app_name, environment=settings.environment)
    yield
    log.info("api_shutdown")


def _error_response(code: int, error_code: str, message: str, detail: object = None) -> JSONResponse:
    """Build the consistent error envelope used across the API."""
    body: dict[str, object] = {"error": {"code": error_code, "message": message}}
    if detail is not None:
        body["error"]["detail"] = detail
    return JSONResponse(status_code=code, content=body)


def _register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to HTTP responses, keeping routes free of try/except."""

    @app.exception_handler(JobNotFoundError)
    async def _not_found(_: Request, exc: JobNotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, "job_not_found", exc.message)

    @app.exception_handler(ResultNotReadyError)
    async def _not_ready(_: Request, exc: ResultNotReadyError) -> JSONResponse:
        return _error_response(status.HTTP_409_CONFLICT, "result_not_ready", exc.message)

    @app.exception_handler(PermanentError)
    async def _bad_request(_: Request, exc: PermanentError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "invalid_request", exc.message)

    @app.exception_handler(TransientError)
    async def _unavailable(_: Request, exc: TransientError) -> JSONResponse:
        log.error("dependency_unavailable", error=exc.message)
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE, "service_unavailable", exc.message
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", "Invalid request", exc.errors()
        )

    @app.exception_handler(PipelineError)
    async def _pipeline(_: Request, exc: PipelineError) -> JSONResponse:
        log.error("unhandled_pipeline_error", error=exc.message)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "Internal server error"
        )


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Meeting Intelligence Pipeline",
        version="1.0.0",
        description="Asynchronous meeting transcription, summarization and action extraction.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)

    app.include_router(routes_health.router, prefix=settings.api_v1_prefix)
    app.include_router(routes_jobs.router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
