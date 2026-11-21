"""Integration ports for independent P1 agents."""

from collections.abc import Sequence
from typing import Literal, Protocol

from .contracts import EpisodeRef, MediaItem, ProfileRules, ReleaseCandidate, SelectionDecision


class IndexerRelease(Protocol):
    candidate: ReleaseCandidate
    download_url: str


class TorrentSnapshot(Protocol):
    hash: str
    name: str
    state: str
    progress: float
    size_bytes: int


class MetadataProvider(Protocol):
    async def search(self, query: str, kind: Literal["all", "movie", "series"] = "all") -> Sequence[MediaItem]: ...


class ReleaseIndexer(Protocol):
    async def search(self, media: MediaItem, episode: EpisodeRef | None = None) -> Sequence[IndexerRelease]: ...


class ReleaseSelector(Protocol):
    def rank(
        self, candidates: Sequence[ReleaseCandidate], media: MediaItem,
        episode: EpisodeRef | None, profile: ProfileRules
    ) -> Sequence[SelectionDecision]: ...


class DownloadClient(Protocol):
    async def add(self, download_url: str, candidate_id: str) -> None: ...

    async def list(self) -> Sequence[TorrentSnapshot]: ...


class LibraryService(Protocol):
    async def scan(self, media: MediaItem) -> list[str]: ...
