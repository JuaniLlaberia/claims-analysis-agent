from pydantic import BaseModel, Field
from typing import Literal

class EvidenceFragment(BaseModel):
    excerpt: str = Field(..., description="Fragment of citation")

class Source(BaseModel):
    url: str = Field(..., description="URL of the source")
    name: str | None = Field(..., description="Name of source")
    fragments: list[EvidenceFragment]
    stance: Literal["supports", "contradicts", "neutral"] = Field(
        ...,
        description="Whether the source 'supports', 'contradicts' or is 'neutral' to the claim based on the citation. Neutral if not explicit."
    )