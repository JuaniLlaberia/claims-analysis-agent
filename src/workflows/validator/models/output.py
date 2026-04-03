from pydantic import BaseModel, Field
from src.workflows.validator.models.source import Source

class CoverageAssessment(BaseModel):
    source_count: int = Field(..., description="Number of independent sources found")
    sources_agree: bool | None = Field(None, description="Whether sources agree with each other. None if only one source or insufficient data")
    evidence_directly_addresses_claim: bool = Field(..., description="Whether the evidence directly addresses the claim or is only tangentially related")
    oldest_source_date: str | None = Field(None, description="Date of the oldest source")
    newest_source_date: str | None = Field(None, description="Date of the newest source")

class ValidatorOutput(BaseModel):
    evidence_summary: str = Field(..., description="Neutral summary of what the sources say about the claim. No verdict, no judgment.")
    coverage: CoverageAssessment
    insufficient_evidence: bool = Field(..., description="True if there is not enough evidence to draw any conclusion for or against the claim")

class CitationsOutput(BaseModel):
    sources: list[Source]