from pydantic import BaseModel, Field
from src.workflows.validator.models.source import Source

class Claim(BaseModel):
    text: str = Field(..., description="Extracted claim as string")
    verified: bool = Field(..., default=False, description="Whether the claim has been verified or not")
    sources: list[Source] = Field(..., description="List of sources with it's evidence about the claim")
