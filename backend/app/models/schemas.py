"""Pydantic models for common API requests and responses."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status", examples=["healthy"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    service: str = Field(default="interview-practice-coach", description="Service name")


class RootResponse(BaseModel):
    message: str = Field(..., description="Welcome message")
    status: str = Field(default="success")
    version: str = Field(..., description="API version")
    docs_url: str = Field(default="/docs", description="Interactive API documentation URL")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="High-level error classification")
    detail: str = Field(..., description="Detailed explanation of the error")
    context: dict[str, Any] | None = Field(default=None, description="Optional diagnostic context")
