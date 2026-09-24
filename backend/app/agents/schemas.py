from pydantic import BaseModel, Field


class QualityReview(BaseModel):
    quality_score: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    passed: bool


class SynthesisOutput(BaseModel):
    recommendation: str
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
