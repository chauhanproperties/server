"""FastAPI application entry point."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.routers.admin import auth, customers, images, properties, queries, stats
from app.routers.public import properties as public_properties
from app.routers.public import queries as public_queries

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chauhan_properties")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    yield
    engine.dispose()

app = FastAPI(
    title="Chauhan Properties API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

for router in (auth.router, properties.router, images.router, queries.router, customers.router, stats.router, public_properties.router, public_queries.router):
    app.include_router(router)

@app.get("/", tags=["health"])
def root():
    return {"message": "Chauhan Properties API"}

@app.get("/health", tags=["health"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        logger.exception("Health check database connection failed")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "unavailable"})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})
