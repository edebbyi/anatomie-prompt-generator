from pydantic import BaseModel, Field


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

