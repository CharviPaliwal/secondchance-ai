"""Internal simulation comparison endpoints."""

from fastapi import APIRouter

from app.services.workflows import run_comparison


router = APIRouter(prefix="/api", tags=["Simulation"])


@router.get("/comparison")
def get_comparison() -> dict:
    """Compare the guarded baseline and SecondChance strategies."""
    return run_comparison()
