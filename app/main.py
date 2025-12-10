from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import OpenAI

from . import airtable_client, llm_agent
from .config import get_settings
from .models import (
    GeneratePromptsRequest,
    GeneratePromptsResponse,
    UpdatePreferencesRequest,
    UpdatePreferencesResponse,
    PreferencesStatusResponse,
)
from .preferences import get_preference_adapter

app = FastAPI(title="Anatomie Prompt Generator")


def _build_llm_client():
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key)
    return None


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Anatomie Prompt Generator API",
        "status": "running",
        "version": "1.1.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    adapter = get_preference_adapter()
    return {
        "status": "healthy",
        "service": "anatomie-prompt-generator",
        "message": "Service is running and ready",
        "preferences_loaded": adapter.has_preferences,
        "structure_scores_loaded": adapter.has_structure_scores,
        "structure_insights_loaded": adapter.has_structure_insights,
        "exploration_rate": adapter.exploration_rate,
    }


@app.post("/generate-prompts", response_model=GeneratePromptsResponse)
async def generate_prompts(request: GeneratePromptsRequest):
    """Generate fashion image prompts."""
    try:
        designers = airtable_client.fetch_designers()
        colors = airtable_client.fetch_colors()
        garments_by_category = airtable_client.fetch_garments_by_category()
        prompt_structures = airtable_client.fetch_prompt_structures(request.renderer)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": f"Airtable error: {exc}"})

    try:
        result = llm_agent.generate_prompts_with_llm(
            num_prompts=request.num_prompts,
            renderer=request.renderer,
            designers=designers,
            colors=colors,
            garments_by_category=garments_by_category,
            prompt_structures=prompt_structures,
            llm_client=_build_llm_client(),
        )
        return result
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


# === PREFERENCE ENDPOINTS ===

@app.post("/update_preferences", response_model=UpdatePreferencesResponse)
async def update_preferences(request: UpdatePreferencesRequest):
    """
    Update preferences, structure scores, and prompt insights.
    
    Called by the Orchestrator after the Optimizer retrains.
    """
    try:
        adapter = get_preference_adapter()
        
        adapter.update(
            preferences=request.global_preference_vector,
            exploration_rate=request.exploration_rate,
            structure_scores=request.structure_scores,
            structure_prompt_insights=request.structure_prompt_insights,
        )
        
        return UpdatePreferencesResponse(
            status="success",
            preferences_count=len(request.global_preference_vector),
            exploration_rate=adapter.exploration_rate,
            structures_with_scores=adapter.structures_with_scores_count,
            structures_with_insights=adapter.structures_with_insights_count,
            message=f"Updated {len(request.global_preference_vector)} preferences, "
                    f"{adapter.structures_with_scores_count} structure scores, "
                    f"{adapter.structures_with_insights_count} structure insights"
        )
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/preferences", response_model=PreferencesStatusResponse)
async def get_preferences():
    """Get current preference status."""
    adapter = get_preference_adapter()
    
    return PreferencesStatusResponse(
        status="loaded" if adapter.has_preferences else "empty",
        has_preferences=adapter.has_preferences,
        has_structure_scores=adapter.has_structure_scores,
        has_structure_insights=adapter.has_structure_insights,
        top_preferences=adapter.get_top_preferences(20),
        exploration_rate=adapter.exploration_rate,
        structures_with_scores=adapter.structures_with_scores_count,
        structures_with_insights=adapter.structures_with_insights_count,
        last_updated=adapter.last_updated,
    )


@app.get("/preferences/structure/{structure_id}")
async def get_structure_preferences(structure_id: str):
    """Get insights and score for a specific structure."""
    adapter = get_preference_adapter()
    
    score = adapter.get_structure_score(structure_id)
    insights = adapter.get_structure_insights(structure_id)
    
    if score is None and insights is None:
        return {
            "status": "not_found",
            "structure_id": structure_id,
            "message": "No data available for this structure"
        }
    
    return {
        "status": "found",
        "structure_id": structure_id,
        "optimizer_score": score,
        "insights": insights
    }


@app.get("/preferences/structures/top")
async def get_top_structures(limit: int = 10):
    """Get structures with highest optimizer scores."""
    adapter = get_preference_adapter()
    
    if not adapter.has_structure_scores:
        return {
            "status": "not_loaded",
            "message": "No structure scores loaded"
        }
    
    return {
        "status": "loaded",
        "top_structures": adapter.get_top_structures(limit),
        "total_structures_with_scores": adapter.structures_with_scores_count
    }


@app.get("/preferences/exploration_stats")
async def get_exploration_stats():
    """Get exploration vs exploitation statistics."""
    adapter = get_preference_adapter()
    return adapter.get_exploration_stats()


@app.post("/preferences/reset_exploration_stats")
async def reset_exploration_stats():
    """Reset exploration statistics counter."""
    adapter = get_preference_adapter()
    adapter.reset_exploration_stats()
    return {"status": "reset", "message": "Exploration stats reset to zero"}


@app.delete("/preferences")
async def clear_preferences():
    """Clear all preferences and reset to defaults."""
    adapter = get_preference_adapter()
    adapter.clear()
    
    return {
        "status": "cleared",
        "message": "Preferences reset to default"
    }
