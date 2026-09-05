"""Internal simulation comparison endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.workflows import run_comparison, run_experiment


router = APIRouter(prefix="/api", tags=["Simulation"])


class SimulationRunRequest(BaseModel):
    scenario: str = "standard"
    seed: int = Field(default=2026, ge=0, le=2_147_483_647)


@router.get("/comparison")
def get_comparison(rerun: bool = Query(default=False)) -> dict:
    """Compare the guarded baseline and SecondChance strategies."""
    return run_comparison(force=rerun)


@router.post("/simulation/run")
def run_simulation(request: SimulationRunRequest) -> dict:
    """Run a real seeded scenario experiment over a derived in-memory cohort."""
    try:
        return run_experiment(request.scenario, request.seed)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
