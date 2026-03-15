"""Structured API error codes and error response envelope.

Every error response from the API includes a machine-readable ``error_code``
alongside the human-readable ``detail`` message.  Clients can switch on
``error_code`` for programmatic error handling instead of parsing strings.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ErrorCode(StrEnum):
    # ── Authentication & Authorization ─────────────────────────────────
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # ── Rate limiting ──────────────────────────────────────────────────
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # ── Resource lifecycle ─────────────────────────────────────────────
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CASE_ALREADY_RESOLVED = "CASE_ALREADY_RESOLVED"
    ALERT_ALREADY_RESOLVED = "ALERT_ALREADY_RESOLVED"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"

    # ── Validation ─────────────────────────────────────────────────────
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    DATASET_NOT_ANALYZABLE = "DATASET_NOT_ANALYZABLE"

    # ── Server ─────────────────────────────────────────────────────────
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API error responses."""

    error_code: ErrorCode
    detail: str
    request_id: str | None = None
