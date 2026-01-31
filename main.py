from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import json
from . import orchestrator
from . import persistence
from . import engine
from . import prompts

# Initialize storage
persistence.init_db()

app = FastAPI(title="REFLEX Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (localhost:5173, 127.0.0.1:5173, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Request Schemas ---
class CreateRunRequest(BaseModel):
    directive: str

class UpdateStageRequest(BaseModel):
    data: Dict[str, Any]

# --- Routes ---

@app.post("/runs")
def create_run(req: CreateRunRequest):
    """Start a new research session."""
    run_id = orchestrator.PipelineManager.create_run(req.directive)
    return {"run_id": run_id, "status": "created"}

@app.get("/runs/{run_id}/state")
def get_run_state(run_id: str, include_provenance: bool = False):
    """
    Fetch full run state. 
    Frontend polls this to update UI.
    """
    try:
        state = persistence.load_run(run_id)
        if not include_provenance:
            # We strip provenance to keep the payload light for the main UI loop
            # Note: In a real app we'd use a response model to filter, 
            # but modifying the dict in memory before return is fine here.
            state_dict = state.dict()
            for stage in state_dict["stages"].values():
                stage["provenance"] = None
            if state_dict["baseline"]:
                state_dict["baseline"]["provenance"] = None
            return state_dict
            
        return state
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")

@app.post("/runs/{run_id}/baseline")
async def run_baseline(run_id: str):
    """
    Execute the single-shot consumer baseline.
    """
    manager = orchestrator.PipelineManager(run_id)
    
    # Update Status
    manager.state.baseline.status = "running"
    persistence.save_run(manager.state)
    
    try:
        response_text, prov = await engine.run_baseline_chat(manager.state.directive)
        
        # Save Result
        manager.state.baseline.data = {"response": response_text}
        manager.state.baseline.provenance = prov
        manager.state.baseline.status = "completed"
        persistence.save_run(manager.state)
        
        return {"status": "baseline_completed"}
        
    except Exception as e:
        manager.state.baseline.status = "failed"
        manager.state.baseline.error = str(e)
        persistence.save_run(manager.state)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/runs/{run_id}/reflex/{stage_name}")
async def run_stage(run_id: str, stage_name: str):
    """
    Execute a specific REFLEX pipeline stage.
    """
    manager = orchestrator.PipelineManager(run_id)
    
    if not manager.can_run_stage(stage_name):
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot run {stage_name}. Check upstream dependencies."
        )

    # 1. Get Config & Context
    config = prompts.STAGE_CONFIGS.get(stage_name)
    if not config:
        raise HTTPException(status_code=400, detail="Invalid stage configuration")
        
    upstream_context = manager.get_upstream_context(stage_name)
    
    # 2. Build Prompt (Constructed dynamically)
    user_prompt = (
        f"RESEARCH DIRECTIVE: {manager.state.directive}\n\n"
        f"UPSTREAM CONTEXT (JSON): {json.dumps(upstream_context, indent=2)}\n\n"
        f"TASK: Generate output strictly following this JSON SCHEMA:\n{config['schema']}"
    )

    # 3. Update Status
    manager.state.stages[stage_name].status = "running"
    persistence.save_run(manager.state)

    try:
        # 4. Call Engine
        data, prov = await engine.call_gemini(
            system_instruction=config['sys'],
            user_prompt=user_prompt,
            temperature=config['temp']
        )

        # 5. Save Result (Orchestrator handles persistence)
        manager.update_stage_data(stage_name, data, provenance=prov)
        
        return {"status": "completed", "stage": stage_name}

    except Exception as e:
        manager.state.stages[stage_name].status = "failed"
        manager.state.stages[stage_name].error = str(e)
        persistence.save_run(manager.state)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/runs/{run_id}/reflex/{stage_name}")
def update_stage_manual(run_id: str, stage_name: str, req: UpdateStageRequest):
    """
    Advanced Mode: User manually edits a stage's output.
    """
    manager = orchestrator.PipelineManager(run_id)
    try:
        # Pass None for provenance since this is a human edit
        manager.update_stage_data(stage_name, req.data, provenance=None)
        return {"status": "updated", "cleared_downstream": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
