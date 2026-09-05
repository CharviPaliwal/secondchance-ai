import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.dashboard import router as dashboard_router
from app.routes.simulation import router as simulation_router
from app.routes.transactions import intelligence_router, router as transactions_router


def get_allowed_origins() -> list[str]:
    """Return explicit frontend origins for development and deployment."""
    configured_origins = os.getenv("ALLOWED_ORIGINS")
    if configured_origins:
        return [
            origin.strip()
            for origin in configured_origins.split(",")
            if origin.strip()
        ]

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
    origins = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    }
    if frontend_url:
        origins.add(frontend_url)
    return sorted(origins)


app = FastAPI(title="SecondChance AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(dashboard_router)
app.include_router(transactions_router)
app.include_router(intelligence_router)
app.include_router(simulation_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "SecondChance AI"}
