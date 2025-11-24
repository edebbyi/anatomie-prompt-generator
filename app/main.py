from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import OpenAI

from . import airtable_client, llm_agent
from .config import get_settings
from .models import GeneratePromptsRequest, GeneratePromptsResponse

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
        "message": "AnatomieE Prompt Generator API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint to wake up service from cold start"""
    return {
        "status": "healthy",
        "service": "anatomie-prompt-generator",
        "message": "Service is running and ready"
    }


@app.post("/generate-prompts", response_model=GeneratePromptsResponse)
async def generate_prompts(request: GeneratePromptsRequest):
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