"""Ports for future independent provider and engine implementations."""

from collections.abc import Sequence
from typing import Protocol

from .contracts import DownloadJob, EpisodeRef, MediaItem, ProfileRules, ReleaseCandidate, SelectionDecision


class MetadataProvider(Protocol):
    async def search(self, query: str) -> Sequence[MediaItem]: ...


class ReleaseIndexer(Protocol):
    async def search(self, media: MediaItem, episode: EpisodeRef | None) -> Sequence[ReleaseCandidate]: ...


class ReleaseSelector(Protocol):
    def rank(self, candidates: Sequence[ReleaseCandidate], profile: ProfileRules) -> Sequence[SelectionDecision]: ...


class DownloadClient(Protocol):
    async def enqueue(self, candidate: ReleaseCandidate, media: MediaItem) -> DownloadJob: ...

    async def get(self, job_id: str) -> DownloadJob: ...


class LibraryService(Protocol):
    async def scan(self, media: MediaItem) -> list[str]: ...
