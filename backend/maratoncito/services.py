"""P1 orchestration and short-lived trusted release lookup."""

import os
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache

from maratoncito.contracts import EpisodeRef, MediaItem, ProfileRules, ReleaseCandidate, SelectionDecision
from maratoncito.integrations.prowlarr import IndexerHit, ProwlarrClient
from maratoncito.integrations.qbittorrent import QBittorrentClient, TorrentProgress
from maratoncito.integrations.tmdb import TMDBClient
from maratoncito.releases.selection import rank_releases


class ConfigurationError(Exception):
    """A required adapter is not configured."""


class CandidateError(Exception):
    """Candidate missing, expired, or disallowed."""


@dataclass
class StoredCandidate:
    hit: IndexerHit
    decision: SelectionDecision
    created_at: float


class CandidateStore:
    """Bounded candidate lookup; tokens expire and never expose torrent URLs in JSON."""

    def __init__(self, ttl_seconds: int = 900, limit: int = 1000) -> None:
        self.ttl_seconds = ttl_seconds
        self.limit = limit
        self._items: OrderedDict[str, StoredCandidate] = OrderedDict()

    def add(self, hit: IndexerHit, decision: SelectionDecision) -> ReleaseCandidate:
        now = time.monotonic()
        self._expire(now)
        token = secrets.token_urlsafe(24)
        candidate = hit.candidate.model_copy(update={"id": token})
        self._items[token] = StoredCandidate(
            hit=IndexerHit(candidate=candidate, download_url=hit.download_url),
            decision=decision.model_copy(update={"candidate_id": token}),
            created_at=now,
        )
        while len(self._items) > self.limit:
            self._items.popitem(last=False)
        return candidate

    def _expire(self, now: float) -> None:
        for token, item in list(self._items.items()):
            if now - item.created_at > self.ttl_seconds:
                del self._items[token]

    def get(self, token: str) -> StoredCandidate:
        self._expire(time.monotonic())
        if token not in self._items:
            raise CandidateError("Selected release expired; search again")
        return self._items[token]


class P1Service:
    def __init__(self) -> None:
        self.tmdb_key = os.getenv("TMDB_API_KEY", "")
        self.prowlarr_key = os.getenv("PROWLARR_API_KEY", "")
        self.prowlarr_url = os.getenv("PROWLARR_URL", "http://prowlarr:9696")
        self.qbit_url = os.getenv("QBITTORRENT_URL", "")
        self.qbit_username = os.getenv("QBITTORRENT_USERNAME", "")
        self.qbit_password = os.getenv("QBITTORRENT_PASSWORD", "")
        self.cache = CandidateStore()

    def capabilities(self) -> dict[str, bool]:
        return {
            "metadata": bool(self.tmdb_key),
            "indexers": bool(self.prowlarr_key and self.prowlarr_url),
            "selection": True,
            "downloads": bool(self.qbit_url),
            "library": False,
            "automation": False,
            "requests": False,
            "subtitles": False,
        }

    def tmdb(self) -> TMDBClient:
        if not self.tmdb_key:
            raise ConfigurationError("TMDB_API_KEY is not configured")
        return TMDBClient(self.tmdb_key)

    def indexer(self) -> ProwlarrClient:
        if not self.prowlarr_key or not self.prowlarr_url:
            raise ConfigurationError("PROWLARR_API_KEY / PROWLARR_URL is not configured")
        return ProwlarrClient(self.prowlarr_url, self.prowlarr_key)

    def downloader(self) -> QBittorrentClient:
        if not self.qbit_url:
            raise ConfigurationError("QBITTORRENT_URL is not configured")
        return QBittorrentClient(self.qbit_url, self.qbit_username, self.qbit_password)

    async def search_catalog(self, query: str, kind: str) -> list[MediaItem]:
        return await self.tmdb().search(query, kind)

    async def search_releases(
        self, media: MediaItem, episode: EpisodeRef | None, profile: ProfileRules
    ) -> list[tuple[ReleaseCandidate, SelectionDecision]]:
        hits = await self.indexer().search(media, episode)
        decisions = rank_releases([hit.candidate for hit in hits], media, episode, profile)
        by_id = {hit.candidate.id: hit for hit in hits}
        output = []
        for decision in decisions:
            candidate = self.cache.add(by_id[decision.candidate_id], decision)
            output.append((candidate, self.cache.get(candidate.id).decision))
        return output

    async def grab(self, candidate_id: str, confirm_unverified: bool) -> str:
        stored = self.cache.get(candidate_id)
        if stored.decision.outcome == "rejected":
            raise CandidateError("This release does not satisfy the requested media or profile")
        if stored.decision.outcome == "needs_review" and not confirm_unverified:
            raise CandidateError("Explicit confirmation is required for unverified releases")
        await self.downloader().add(stored.hit.download_url, candidate_id)
        return "submitted"

    async def downloads(self) -> list[TorrentProgress]:
        return await self.downloader().list()


@lru_cache(maxsize=1)
def get_service() -> P1Service:
    return P1Service()
