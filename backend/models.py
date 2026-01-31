from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Standardized Stage Names
STAGE_ORDER = ["intent", "decomposition", "claims", "critique", "revision", "evaluation"]

class Provenance(BaseModel):
    """Auditable metadata for a specific stage execution."""
    prompt: str
    model_name: str
    model_params: Dict[str, Any]
    raw_response: str
    repair_attempts: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StageStore(BaseModel):
    """The state of a single stage."""
    status: str = "pending"  # pending, running, completed, failed
    data: Optional[Dict[str, Any]] = None
    provenance: Optional[Provenance] = None
    
    # Explicit error message field for UI clarity
    error: Optional[str] = None

class RunState(BaseModel):
    """The root object for a full research run."""
    run_id: str
    directive: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Baseline is separate from the pipeline
    baseline: StageStore = Field(default_factory=StageStore)
    
    # The core pipeline stages, initialized safely using a factory
    stages: Dict[str, StageStore] = Field(default_factory=lambda: {
        stage: StageStore() for stage in STAGE_ORDER
    })
