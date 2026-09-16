import os
import sys
# Add monorepo root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.api.system import router as system_router
from app.api.auth import router as auth_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oiltrace")

def seed_default_users():
    db = SessionLocal()
    try:
        default_users = [
            ("Lead Investigator", "admin@oiltrace.org", "AdminPass2026!", UserRole.ADMIN),
            ("Maritime Analyst", "analyst@oiltrace.org", "AnalystPass2026!", UserRole.ANALYST),
            ("Operations Viewer", "viewer@oiltrace.org", "ViewerPass2026!", UserRole.VIEWER),
        ]
        for name, email, password, role in default_users:
            existing = db.query(User).filter(User.email == email).first()
            if not existing:
                u = User(
                    name=name,
                    email=email,
                    password_hash=get_password_hash(password),
                    role=role,
                )
                db.add(u)
        db.commit()
        logger.info("Default seed users verified.")
    except Exception as e:
        logger.error(f"Error seeding default users: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OILTRACE Marine Decision Support API...")
    seed_default_users()
    yield
    logger.info("Shutting down OILTRACE API...")

app = FastAPI(
    title="OILTRACE API",
    description=(
        "OILTRACE — AI-Powered Marine Oil Spill Detection, Drift Reconstruction "
        "and Vessel Attribution System (Smart India Hackathon 2026 Problem Statement SIH26143).\n\n"
        "IMPORTANT: This is a scientific decision-support system. It produces explainable, "
        "ranked candidate vessels and never establishes legal responsibility."
    ),
    version="1.0.0-prototype",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Consistent Error Handling
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
    }
    error_code = code_map.get(exc.status_code, "API_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": exc.detail if isinstance(exc.detail, str) else "Request processing error.",
                "details": exc.detail if not isinstance(exc.detail, str) else None,
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input format or missing required fields.",
                "details": exc.errors(),
            }
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
            }
        },
    )

from app.api.ais import router as ais_router
from app.api.satellite import router as satellite_router
from app.api.spills import router as spills_router
from app.api.detection import router as detection_router
from app.api.drift import router as drift_router
from app.api.attribution import router as attribution_router
from app.api.investigations import router as investigations_router
from app.api.reports import router as reports_router
from app.api.demo import router as demo_router

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(ais_router)
app.include_router(satellite_router)
app.include_router(spills_router)
app.include_router(detection_router)
app.include_router(drift_router)
app.include_router(attribution_router)
app.include_router(investigations_router)
app.include_router(reports_router)
app.include_router(demo_router)

