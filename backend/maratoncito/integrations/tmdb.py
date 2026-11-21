"""TMDB metadata search adapter."""

import httpx

from maratoncito.contracts import MediaItem


class ProviderError(Exception):
    """A configured external service could not complete a request."""


class TMDBClient:
    def __init__(self, api_key: str, base_url: str = "https://api.themoviedb.org") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, kind: str = "all") -> list[MediaItem]:
        endpoint = {
            "all": "multi",
            "movie": "movie",
            "series": "tv",
        }[kind]
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=15) as client:
                response = await client.get(
                    f"/3/search/{endpoint}",
                    params={"api_key": self.api_key, "query": query, "include_adult": "false"},
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("TMDB metadata search failed") from exc

        items: list[MediaItem] = []
        for row in data.get("results", [])[:30]:
            media_type = row.get("media_type", endpoint)
            if media_type not in {"movie", "tv"}:
                continue
            target_kind = "series" if media_type == "tv" else "movie"
            title = row.get("name") if target_kind == "series" else row.get("title")
            date = row.get("first_air_date") if target_kind == "series" else row.get("release_date")
            if not title or not isinstance(row.get("id"), int):
                continue
            year = int(date[:4]) if isinstance(date, str) and len(date) >= 4 and date[:4].isdigit() else None
            items.append(
                MediaItem(
                    id=f"tmdb:{media_type}:{row['id']}",
                    kind=target_kind,
                    title=title,
                    year=year,
                    tmdb_id=row["id"],
                    original_language=row.get("original_language"),
                )
            )
        return items
