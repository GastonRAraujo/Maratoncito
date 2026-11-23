"""qBittorrent Web API client. Credentials and URLs are server-side only."""

from dataclasses import dataclass

import httpx

from maratoncito.integrations.tmdb import ProviderError


@dataclass(frozen=True)
class TorrentProgress:
    hash: str
    name: str
    state: str
    progress: float
    size_bytes: int


class QBittorrentClient:
    def __init__(self, url: str, username: str, password: str, category: str = "maratoncito") -> None:
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.category = category

    async def _authenticate(self, client: httpx.AsyncClient) -> None:
        if not self.username and not self.password:
            return
        response = await client.post(
            "/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
        )
        if response.status_code != 200 or response.text.strip() != "Ok.":
            raise ProviderError("qBittorrent authentication failed")

    async def _ensure_category(self, client: httpx.AsyncClient) -> None:
        categories = await client.get("/api/v2/torrents/categories")
        categories.raise_for_status()
        data = categories.json()
        if self.category not in data:
            response = await client.post("/api/v2/torrents/createCategory", data={"category": self.category})
            response.raise_for_status()

    async def add(self, download_url: str, candidate_id: str) -> None:
        try:
            async with httpx.AsyncClient(base_url=self.url, timeout=15) as client:
                await self._authenticate(client)
                await self._ensure_category(client)
                response = await client.post(
                    "/api/v2/torrents/add",
                    data={"urls": download_url, "category": self.category, "tags": f"maratoncito-{candidate_id}"},
                )
                response.raise_for_status()
                if response.text.strip() != "Ok.":
                    raise ProviderError("qBittorrent rejected the release")
        except httpx.HTTPError as exc:
            raise ProviderError("Unable to submit the torrent to qBittorrent") from exc

    async def list(self) -> list[TorrentProgress]:
        try:
            async with httpx.AsyncClient(base_url=self.url, timeout=15) as client:
                await self._authenticate(client)
                response = await client.get("/api/v2/torrents/info", params={"category": self.category})
                response.raise_for_status()
                rows = response.json()
                if not isinstance(rows, list):
                    raise ProviderError("Unexpected qBittorrent download response")
                return [
                    TorrentProgress(
                        hash=str(row.get("hash", "")),
                        name=str(row.get("name", "")),
                        state=str(row.get("state", "unknown")),
                        progress=min(1.0, max(0.0, float(row.get("progress", 0)))),
                        size_bytes=max(0, int(row.get("size", 0))),
                    )
                    for row in rows
                ]
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError("Unable to read qBittorrent downloads") from exc
