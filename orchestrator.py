import uuid
from typing import Dict, Any
from .models import RunState, StageStore, STAGE_ORDER
from . import persistence

class PipelineManager:
    def __init__(self, run_id: str = None):
        if run_id:
            self.state = persistence.load_run(run_id)
        else:
            raise ValueError("PipelineManager requires an existing run_id")

    @staticmethod
    def create_run(directive: str) -> str:
        """Initialize a new run."""
        run_id = str(uuid.uuid4())[:8]  # Short IDs for readability
        state = RunState(run_id=run_id, directive=directive)
        persistence.save_run(state)
        return run_id

    def get_stage_status(self, stage_name: str) -> str:
        return self.state.stages[stage_name].status

    def can_run_stage(self, stage_name: str) -> bool:
        """Check if upstream dependencies are met."""
        if stage_name not in STAGE_ORDER:
            return False
            
        idx = STAGE_ORDER.index(stage_name)
        if idx == 0:
            return True
            
        # Check previous stage
        prev_stage = STAGE_ORDER[idx - 1]
        return self.state.stages[prev_stage].status == "completed"

    def update_stage_data(self, stage_name: str, data: Dict[str, Any], provenance=None):
        """
        Update a stage's data. 
        If this is an edit (Advanced Mode), it clears downstream stages.
        """
        if stage_name not in STAGE_ORDER:
            raise ValueError(f"Invalid stage: {stage_name}")

        # Update the target stage
        self.state.stages[stage_name].data = data
        self.state.stages[stage_name].status = "completed"
        if provenance:
            self.state.stages[stage_name].provenance = provenance

        # CLEAR DOWNSTREAM LOGIC
        # Find index and reset everything after it
        idx = STAGE_ORDER.index(stage_name)
        downstream_stages = STAGE_ORDER[idx + 1:]
        
        for ds in downstream_stages:
            # Reset to clean state
            self.state.stages[ds] = StageStore(status="pending")
            
        persistence.save_run(self.state)

    def get_upstream_context(self, stage_name: str) -> Dict[str, Any]:
        """
        Retrieve data from all stages prior to the current one.
        Used to build the prompt context.
        """
        idx = STAGE_ORDER.index(stage_name)
        upstream = STAGE_ORDER[:idx]
        context = {}
        for s in upstream:
            # We assume upstream stages are completed if we are running this.
            # If not, the prompt builder might see None, which is fine/handleable.
            context[s] = self.state.stages[s].data
        return context
