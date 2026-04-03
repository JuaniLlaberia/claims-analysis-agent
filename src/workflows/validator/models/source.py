from pydantic import BaseModel, Field

class EvidenceFragment(BaseModel):
    excerpt: str = Field(..., description="Fragment of citation")

class Source(BaseModel):
    url: str = Field(..., description="URL of the source")
    name: str | None = Field(..., description="Name of source")
    fragments: list[EvidenceFragment]