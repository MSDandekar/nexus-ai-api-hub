import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.seed import seed_database
from backend.routers import (
    health, connectors, gateway, analytics, evaluations, blueprint, keys, models_info
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_nexus.app")

from backend.core.config import settings, get_gemini_api_key, get_openai_api_key, get_groq_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Nexus Database & Seeds...")
    try:
        await seed_database()
        logger.info(
            f"AI Providers status — Gemini configured: {bool(get_gemini_api_key())}, "
            f"OpenAI configured: {bool(get_openai_api_key())}, "
            f"Groq configured: {bool(get_groq_api_key())}"
        )
        logger.info("AI Nexus initialized successfully.")
    except Exception as e:
        logger.error(f"Startup initialization warning: {e}")
    yield
    logger.info("AI Nexus shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="One API. Any AI. Intelligent routing. Production AI Gateway.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe error handler - Section 24
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please contact the administrator.",
                "details": [str(exc)] if settings.ENVIRONMENT == "development" else []
            },
            "meta": {
                "path": request.url.path
            }
        }
    )

# Include API Routers
app.include_router(health.router)
app.include_router(connectors.router)
app.include_router(gateway.router)
app.include_router(analytics.router)
app.include_router(evaluations.router)
app.include_router(blueprint.router)
app.include_router(keys.router)
app.include_router(models_info.router)

# Mount static frontend build if present
static_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(static_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Allow API routes to pass through
        if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        file_path = os.path.join(static_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dist, "index.html"))
else:
    @app.get("/", include_in_schema=False)
    async def root_placeholder():
        return {
            "name": settings.PROJECT_NAME,
            "tagline": "One API. Any AI. Intelligent routing.",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health"
        }
