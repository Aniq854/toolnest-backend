"""
Request / response ke shapes (Pydantic models).
"""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

Tone = Literal["casual", "professional", "academic", "blog", "simple", "storytelling"]


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Rewrite karne wala text")
    tone: Tone = "blog"
    reading_level: Literal["easy", "medium", "advanced"] = "medium"
    strength: int = Field(2, ge=1, le=3, description="1=light edit, 3=heavy rewrite")
    keep_length: bool = True
    provider: Optional[str] = None  # UI se override karne ke liye
    profile_id: Optional[str] = None  # "meri awaaz mein likho"


class Metrics(BaseModel):
    words: int
    sentences: int
    avg_sentence_len: float
    sentence_len_stdev: float
    long_word_pct: float
    flesch_reading_ease: float
    passive_hits: int
    cliche_hits: int
    bureaucracy_hits: int = 0
    naturalness_score: float


class HumanizeResponse(BaseModel):
    output: str
    provider_used: str
    model_used: str
    before: Metrics
    after: Metrics
    notes: list[str] = []
    voice_match: Optional[float] = None
    voice_gaps: list[str] = []
    profile_used: Optional[str] = None
    repair_used: bool = False


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=20)


class AnalyzeResponse(BaseModel):
    metrics: Metrics
    suggestions: list[str]


# ---------- Style profiles ----------


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    samples: list[str] = Field(
        ...,
        min_length=1,
        description="User ke apne likhe hue 2-5 samples (kam az kam 150 lafz total)",
    )
    provider: Optional[str] = None


class ProfileSummary(BaseModel):
    id: str
    name: str
    created_at: str
    sample_word_count: int
    voice_summary: str = ""


class ProfileDetail(BaseModel):
    id: str
    name: str
    created_at: str
    sample_word_count: int
    fingerprint: dict[str, Any]
    traits: dict[str, Any]


class SentenceRequest(BaseModel):
    sentence: str = Field(..., min_length=5, max_length=1000)
    profile_id: Optional[str] = None
    tone: Tone = "blog"
    provider: Optional[str] = None


class SentenceResponse(BaseModel):
    output: str
