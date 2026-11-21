"""Prowlarr search adapter and normalized result mapping."""

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx

from maratoncito.contracts import EpisodeRef, MediaItem, ReleaseCandidate
from maratoncito.integrations.tmdb import ProviderError
from maratoncito.releases.parser import parse_release


@dataclass(frozen=True)
class IndexerHit:
    candidate: ReleaseCandidate
    download_url: str


def _identity(row: dict) -> str:
    magnet = row.get("magnetUrl") or ""
    if magnet:
        query = parse_qs(urlparse(magnet).query)
        xt = query.get("xt", [""])[0]
        if xt.lower().startswith("urn:btih:"):
            return xt.lower()
    title = re.sub(r"\W+", "", str(row.get("title", "")).lower())
    return f"{title}:{row.get('size', '')}"


class ProwlarrClient:
    def __init__(self, url: str, api_key: str) -> None:
        self.url = url.rstrip("/")
        self.api_key = api_key

    async def search(self, media: MediaItem, episode: EpisodeRef | None = None) -> list[IndexerHit]:
        query = media.title
        if episode is not None:
            query += f" S{episode.season_number:02d}E{episode.episode_number:02d}"
        elif media.year:
            query += f" {media.year}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.url}/api/v1/search",
                    headers={"X-Api-Key": self.api_key},
                    params={"query": query, "type": "search", "indexerIds": -1},
                )
                response.raise_for_status()
                rows = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("Prowlarr release search failed") from exc

        if not isinstance(rows, list):
            raise ProviderError("Prowlarr returned an unexpected search result")

        found: dict[str, IndexerHit] = {}
        for row in rows[:200]:
            title = row.get("title")
            url = row.get("magnetUrl") or row.get("downloadUrl")
            if not isinstance(title, str) or not isinstance(url, str) or not url.startswith(("magnet:?", "http://", "https://")):
                continue
            identity = _identity(row)
            value = hashlib.sha256(identity.encode()).hexdigest()[:32]
            seeders = row.get("seeders") if isinstance(row.get("seeders"), int) else None
            size = row.get("size") if isinstance(row.get("size"), int) else None
            candidate = ReleaseCandidate(
                id=value,
                title=title,
                indexer=str(row.get("indexer") or row.get("indexerId") or "unknown"),
                size_bytes=max(size, 0) if size is not None else None,
                seeders=max(seeders, 0) if seeders is not None else None,
                parsed=parse_release(title),
            )
            hit = IndexerHit(candidate=candidate, download_url=url)
            previous = found.get(identity)
            if previous is None or (hit.candidate.seeders or 0) > (previous.candidate.seeders or 0):
                found[identity] = hit
        return list(found.values())
