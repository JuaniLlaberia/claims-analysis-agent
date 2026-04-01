from pydantic import BaseModel, Field

class SnippetAnalysisOutput(BaseModel):
    claims: list[str] = Field(..., description="List of extracted claims from given text. It can be empty if none are present.")

class ClaimsNormalizationOutput(BaseModel):
    claims: list[str] = Field(..., description="List of normalized and syntactically well written claims extracted from the raw claims.")