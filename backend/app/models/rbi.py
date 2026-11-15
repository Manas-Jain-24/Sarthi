"""Evidence and analysis contracts for the real RBI document path."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Paragraph(StrictModel):
    id: str
    text: str


class RBIDocument(StrictModel):
    id: str
    title: str
    source_url: str
    published_on: str
    retrieved_at: str
    raw_sha256: str
    text_sha256: str
    paragraphs: list[Paragraph]
    archive_file: str
    parser_version: str = "rbi-table-v1"


class Citation(StrictModel):
    paragraph_id: str
    quote: str = Field(min_length=12, max_length=500)


class EvidenceClaim(StrictModel):
    kind: Literal["fact", "interpretation"]
    text: str = Field(min_length=12, max_length=800)
    citations: list[Citation] = Field(min_length=1, max_length=3)


class RBIAnalysis(StrictModel):
    abstain: bool
    abstention_reason: str = Field(max_length=600)
    claims: list[EvidenceClaim] = Field(max_length=6)
    affected_sectors: list[Literal["Banking", "NBFCs", "Real Estate", "Automotive"]] = Field(max_length=4)
    uncertainties: list[str] = Field(min_length=1, max_length=5)
    counterarguments: list[str] = Field(min_length=1, max_length=4)
    repo_rate_pct: float | None


class AnalysisRecord(StrictModel):
    document_id: str
    text_sha256: str
    requested_model: str
    resolved_model: str
    prompt_version: str
    generated_at: str
    analysis: RBIAnalysis


class AnalysisUnavailable(Exception):
    """An actionable, non-secret error suitable for display to the user."""
