import json
import os
from datetime import datetime
from .models import RunState, StageStore

RUNS_DIR = os.path.join(os.path.dirname(__file__), "runs")

def _get_path(run_id: str) -> str:
    return os.path.join(RUNS_DIR, f"{run_id}.json")

def init_db():
    """Ensure runs directory exists."""
    if not os.path.exists(RUNS_DIR):
        os.makedirs(RUNS_DIR)

def save_run(state: RunState):
    """Persist the run state to disk."""
    state.last_updated = datetime.utcnow()
    path = _get_path(state.run_id)
    
    # Using Pydantic's model_dump_json for reliable serialization
    with open(path, "w") as f:
        f.write(state.model_dump_json(indent=2))

def load_run(run_id: str) -> RunState:
    """Load a run state from disk."""
    path = _get_path(run_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Run {run_id} not found.")
    
    with open(path, "r") as f:
        data = json.load(f)
        return RunState(**data)

def list_runs():
    """Helper to list all available run IDs (for debugging)."""
    if not os.path.exists(RUNS_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(RUNS_DIR) if f.endswith(".json")]
