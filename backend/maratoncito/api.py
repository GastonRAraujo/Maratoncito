"""Manual discovery, release selection, and torrent queue API."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from maratoncito.contracts import EpisodeRef, MediaItem, ProfileRules, ReleaseCandidate, SelectionDecision
from maratoncito.integrations.tmdb import ProviderError
from maratoncito.services import CandidateError, ConfigurationError, P1Service, get_service

router = APIRouter(prefix="/api/v1", tags=["discovery"])
Service = Annotated[P1Service, Depends(get_service)]


class ReleaseSearch(BaseModel):
    media: MediaItem
    episode: EpisodeRef | None = None
    profile: ProfileRules = Field(default_factory=ProfileRules)


class ReleaseMatch(BaseModel):
    candidate: ReleaseCandidate
    decision: SelectionDecision


class GrabRequest(BaseModel):
    candidate_id: str = Field(min_length=16, max_length=80)
    confirm_unverified: bool = False


class GrabResponse(BaseModel):
    candidate_id: str
    status: Literal["submitted"]


class DownloadInfo(BaseModel):
    hash: str
    name: str
    state: str
    progress: float
    size_bytes: int


def raise_http(exc: Exception) -> None:
    if isinstance(exc, ConfigurationError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, CandidateError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ProviderError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    raise exc


@router.get("/catalog/search", response_model=list[MediaItem])
async def catalog_search(
    service: Service,
    q: Annotated[str, Query(min_length=2, max_length=150)],
    kind: Literal["all", "movie", "series"] = "all",
) -> list[MediaItem]:
    try:
        return await service.search_catalog(q, kind)
    except (ConfigurationError, ProviderError) as exc:
        raise_http(exc)


@router.post("/releases/search", response_model=list[ReleaseMatch])
async def release_search(body: ReleaseSearch, service: Service) -> list[ReleaseMatch]:
    if body.media.kind == "series" and body.episode is None:
        raise HTTPException(status_code=422, detail="A specific episode is required for a series search")
    if body.episode is not None and (body.media.kind != "series" or body.episode.series_id != body.media.id):
        raise HTTPException(status_code=422, detail="Episode must belong to the selected series")
    try:
        results = await service.search_releases(body.media, body.episode, body.profile)
        return [ReleaseMatch(candidate=candidate, decision=decision) for candidate, decision in results]
    except (ConfigurationError, ProviderError) as exc:
        raise_http(exc)


@router.post("/downloads", response_model=GrabResponse)
async def grab_release(body: GrabRequest, service: Service) -> GrabResponse:
    try:
        await service.grab(body.candidate_id, body.confirm_unverified)
        return GrabResponse(candidate_id=body.candidate_id, status="submitted")
    except (ConfigurationError, CandidateError, ProviderError) as exc:
        raise_http(exc)


@router.get("/downloads", response_model=list[DownloadInfo])
async def download_queue(service: Service) -> list[DownloadInfo]:
    try:
        return [DownloadInfo(**item.__dict__) for item in await service.downloads()]
    except (ConfigurationError, ProviderError) as exc:
        raise_http(exc)
