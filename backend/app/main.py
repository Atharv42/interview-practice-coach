"""Main FastAPI application entrypoint for Interview Practice Coach."""

import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.analytics import router as analytics_router
from app.api.audio import router as audio_router
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.api.visual import router as visual_router
from app.models.schemas import RootResponse

APP_TITLE = "Interview Practice Coach API"
APP_DESCRIPTION = (
    "Objective feedback backend for interview delivery mechanics "
    "(speaking pace, filler words, pauses, and geometric visual indicators). "
    "Does not infer emotions or personality."
)
APP_VERSION = "0.1.0"

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
if not allowed_origins:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "The request body or parameters failed validation.",
            "context": {"errors": exc.errors()},
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "context": {"status_code": exc.status_code},
        },
    )


# Include modular routers
app.include_router(health_router)
app.include_router(audio_router, prefix="/api/v1")
app.include_router(visual_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")


@app.get("/", response_model=RootResponse, summary="API Root")
def root() -> RootResponse:
    """Root endpoint welcoming clients and directing them to API documentation."""
    return RootResponse(
        message="Interview Practice Coach backend is running!",
        status="success",
        version=APP_VERSION,
        docs_url="/docs",
    )
