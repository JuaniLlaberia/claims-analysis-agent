from pydantic import BaseModel, Field
from src.workflows.validator.models.source import Source
from src.workflows.validator.models.output import CoverageAssessment

class Claim(BaseModel):
    text: str = Field(..., description="Extracted claim as string")
    evidence_found: bool = Field(..., description="Whether evidence was found for or against the claim")
    sources: list[Source] = Field(..., description="List of sources with evidence about the claim")

class AnalyzedClaim(BaseModel):
    claim: Claim = Field(..., description="Claim information with text, evidence and sources")
    evidence_summary: str = Field(..., description="Generated summary based on claim evidence")
    coverage: CoverageAssessment
    insufficient_evidence: bool