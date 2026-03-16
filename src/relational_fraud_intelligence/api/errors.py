"""Structured error envelope types for consistent API error responses."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Machine-readable error codes returned in every error response."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorResponse(BaseModel):
    """Standard error envelope returned for all non-2xx API responses."""

    error_code: ErrorCode
    detail: str
    request_id: str | None = None

