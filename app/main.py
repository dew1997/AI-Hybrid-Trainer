from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,
        )
    logger.info("startup", environment=settings.environment)
    yield
    logger.info("shutdown")


app = FastAPI(
    title="AI Hybrid Training Intelligence Platform",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "title": type(exc).__name__,
            "status": exc.status_code,
            "detail": exc.message,
            "instance": str(request.url.path),
        },
    )


from app.api.router import router  # noqa: E402

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/health/ready", tags=["health"])
async def health_ready():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    import redis.asyncio as aioredis

    checks = {}
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    all_ok = all(v["status"] == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )


# SPA fallback — must be last so it never shadows API or health routes.
# Serves real files from dist/ (favicon, robots.txt, etc.) and falls back
# to index.html for all client-side routes.
_DIST = Path("frontend/dist")
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        file = _DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_DIST / "index.html")
