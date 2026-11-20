"""Shared boundary contracts; integrations depend on these types."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MediaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["movie", "series"]
    title: str
    year: int | None = None
    tmdb_id: int | None = None
    tvdb_id: int | None = None
    original_language: str | None = None


class EpisodeRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_id: str
    season_number: int = Field(ge=0)
    episode_number: int = Field(ge=1)


class ParsedRelease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["movie", "episode", "season_pack", "unknown"] = "unknown"
    resolution: str | None = None
    source: str | None = None
    codec: str | None = None
    release_group: str | None = None
    audio_languages: list[str] = Field(default_factory=list)
    subtitle_languages: list[str] = Field(default_factory=list)
    season_number: int | None = Field(default=None, ge=0)
    episode_numbers: list[int] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ReleaseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    indexer: str
    size_bytes: int | None = Field(default=None, ge=0)
    seeders: int | None = Field(default=None, ge=0)
    parsed: ParsedRelease = Field(default_factory=ParsedRelease)


class SelectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    outcome: Literal["accepted", "rejected", "needs_review"]
    score: float | None = None
    reasons: list[str] = Field(default_factory=list)


class ReleaseGroupPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["any", "prefer", "require", "regex"] = "any"
    value: str | None = None

    @model_validator(mode="after")
    def validate_value(self) -> "ReleaseGroupPolicy":
        if self.mode == "any" and self.value is not None:
            raise ValueError("A group value is not allowed for the 'any' mode")
        if self.mode != "any" and not self.value:
            raise ValueError("A group value is required for this mode")
        return self


class ProfileRules(BaseModel):
    """Resolved profile with concrete values; no inheritance markers."""

    model_config = ConfigDict(extra="forbid")

    resolutions: list[str] = Field(default_factory=lambda: ["1080p"])
    audio_mode: Literal["original", "prefer", "any"] = "original"
    preferred_audio_languages: list[str] = Field(default_factory=list)
    subtitle_languages: list[str] = Field(default_factory=lambda: ["es"])
    release_group: ReleaseGroupPolicy = Field(default_factory=ReleaseGroupPolicy)


class ProfileOverride(BaseModel):
    """Fields omitted from an override inherit their parent values.

    A null value is *not* an instruction to clear the parent. Clearing behavior
    will be designed explicitly before the profile engine is implemented.
    """

    model_config = ConfigDict(extra="forbid")

    resolutions: list[str] | None = None
    audio_mode: Literal["original", "prefer", "any"] | None = None
    preferred_audio_languages: list[str] | None = None
    subtitle_languages: list[str] | None = None
    release_group: ReleaseGroupPolicy | None = None


class DownloadStatus(StrEnum):
    queued = "queued"
    downloading = "downloading"
    completed = "completed"
    failed = "failed"
    importing = "importing"
    imported = "imported"


class DownloadJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    media_id: str
    candidate_id: str
    status: DownloadStatus
    progress: float = Field(default=0, ge=0, le=1)
    error: str | None = None
