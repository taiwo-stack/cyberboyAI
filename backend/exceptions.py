"""
exceptions.py — Domain exception hierarchy + FastAPI error handlers

Design goals
────────────
1. Never leak internal details (stack traces, DB errors, file paths) to API clients.
2. All exceptions carry a ``safe_message`` that is safe to return to callers.
3. Full tracebacks are logged server-side via the standard ``logging`` module.
4. HTTP status codes are determined by exception type, not by the caller.
"""

import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("gaudon")


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class GaudonError(Exception):
    """Base class for all GaudOn application errors."""

    http_status: int = 500
    safe_message: str = "An unexpected error occurred. Please try again."

    def __init__(self, internal_detail: str = "", safe_message: str | None = None):
        self.internal_detail = internal_detail
        if safe_message:
            self.safe_message = safe_message
        super().__init__(internal_detail or self.safe_message)


class AnalysisError(GaudonError):
    """Raised when the analysis pipeline fails for a specific input."""

    http_status = 500
    safe_message = "Analysis failed due to an internal error. Please try again."


class ServiceUnavailableError(GaudonError):
    """Raised when a required downstream service (DB, OpenAI, etc.) is unreachable."""

    http_status = 503
    safe_message = "A required service is temporarily unavailable. Please try again shortly."


class InputValidationError(GaudonError):
    """Raised when the request input fails domain-level validation."""

    http_status = 422
    safe_message = "The provided input is invalid or could not be processed."


class NotFoundError(GaudonError):
    """Raised when a requested resource does not exist."""

    http_status = 404
    safe_message = "The requested resource was not found."


class AuthorizationError(GaudonError):
    """Raised when an admin action fails the secret-key check."""

    http_status = 401
    safe_message = "Unauthorized."


# ── FastAPI Exception Handlers ─────────────────────────────────────────────────

async def gaudon_error_handler(request: Request, exc: GaudonError) -> JSONResponse:
    """
    Handles all GaudonError subclasses.
    Logs the full internal detail server-side; returns only the safe_message to the client.
    """
    logger.error(
        "GaudonError [%s] on %s %s: %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc.internal_detail or str(exc),
    )
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": exc.safe_message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any exception that is NOT a GaudonError.
    Prevents internal details from ever reaching the client.
    """
    logger.error(
        "Unhandled exception on %s %s:\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected server error occurred. Please try again."},
    )
