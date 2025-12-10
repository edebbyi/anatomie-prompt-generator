from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class GeneratePromptsRequest(BaseModel):
    request_id: str | None = None
    num_prompts: int = Field(..., gt=0)
    renderer: str = Field(..., min_length=1)


class PromptItem(BaseModel):
    promptText: str
    designerId: str
    garmentId: str
    promptStructureId: str
    renderer: str


class GeneratePromptsResponse(BaseModel):
    prompts: list[PromptItem]


# === PREFERENCE MODELS ===

class PromptInsightItem(BaseModel):
    """Single prompt performance record."""
    prompt_hash: Optional[str] = None
    prompt_preview: str
    success_rate: float
    sample_count: Optional[int] = None


class StructurePromptInsight(BaseModel):
    """Prompt performance data for a specific structure."""
    top_prompts: List[PromptInsightItem]
    avg_success_rate: float


class UpdatePreferencesRequest(BaseModel):
    """Request from Orchestrator to update preferences, scores, and insights."""
    global_preference_vector: Dict[str, float]
    exploration_rate: Optional[float] = None
    structure_scores: Optional[Dict[str, float]] = None
    structure_prompt_insights: Optional[Dict[str, Any]] = None


class UpdatePreferencesResponse(BaseModel):
    """Response confirming preference update."""
    status: str
    preferences_count: int
    exploration_rate: float
    structures_with_scores: int
    structures_with_insights: int
    message: str


class PreferencesStatusResponse(BaseModel):
    """Current preferences status."""
    status: str
    has_preferences: bool
    has_structure_scores: bool
    has_structure_insights: bool
    top_preferences: Dict[str, float]
    exploration_rate: float
    structures_with_scores: int
    structures_with_insights: int
    last_updated: Optional[str] = None
