import httpx
import pytest

from maratoncito.contracts import MediaItem
from maratoncito.integrations import prowlarr, qbittorrent, tmdb


@pytest.mark.asyncio
async def test_tmdb_maps_movies_and_series(monkeypatch) -> None:
    async def _not_used():
        pass

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/3/search/multi"
        assert request.url.params["api_key"] == "test-key"
        return httpx.Response(200, json={"results": [
            {"id": 1, "media_type": "movie", "title": "Example Film", "release_date": "2024-01-01", "original_language": "en"},
            {"id": 2, "media_type": "tv", "name": "Example Show", "first_air_date": "2025-09-01"},
            {"id": 3, "media_type": "person", "name": "Nobody"},
        ]})

    original = httpx.AsyncClient
    monkeypatch.setattr(tmdb.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    found = await tmdb.TMDBClient("test-key").search("Example")
    assert [item.kind for item in found] == ["movie", "series"]
    assert found[0].year == 2024


@pytest.mark.asyncio
async def test_prowlarr_deduplicates_release_and_preserves_download_url(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/search"
        assert request.url.params["type"] == "search"
        assert request.headers["X-Api-Key"] == "test-key"
        return httpx.Response(200, json=[
            {"title": "Example.Film.2024.1080p.WEB-DL-GROUPX", "downloadUrl": "https://indexer.example/a", "size": 1000, "seeders": 5, "indexer": "A"},
            {"title": "Example.Film.2024.1080p.WEB-DL-GROUPX", "downloadUrl": "https://indexer.example/b", "size": 1000, "seeders": 27, "indexer": "B"},
        ])

    original = httpx.AsyncClient
    monkeypatch.setattr(prowlarr.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    media = MediaItem(id="tmdb:movie:1", kind="movie", title="Example Film", year=2024)
    results = await prowlarr.ProwlarrClient("http://prowlarr:9696", "test-key").search(media)
    assert len(results) == 1
    assert results[0].candidate.seeders == 27
    assert results[0].download_url == "https://indexer.example/b"


@pytest.mark.asyncio
async def test_qbittorrent_login_enqueue_and_read_progress(monkeypatch) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v2/auth/login":
            return httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=valid; Path=/"})
        if request.url.path == "/api/v2/torrents/categories":
            return httpx.Response(200, json={})
        if request.url.path == "/api/v2/torrents/createCategory":
            return httpx.Response(200, text="Ok.")
        if request.url.path == "/api/v2/torrents/add":
            assert "category=maratoncito" in request.content.decode()
            return httpx.Response(200, text="Ok.")
        if request.url.path == "/api/v2/torrents/info":
            assert request.url.params["category"] == "maratoncito"
            return httpx.Response(200, json=[{"hash": "abc", "name": "Example", "state": "downloading", "progress": 0.4, "size": 1024}])
        raise AssertionError(f"Unexpected call: {request.url.path}")

    original = httpx.AsyncClient
    monkeypatch.setattr(qbittorrent.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    client = qbittorrent.QBittorrentClient("http://qbit:8080", "admin", "password")
    await client.add("magnet:?xt=urn:btih:ABC", "candidate")
    queue = await client.list()
    assert queue[0].progress == 0.4
    assert "/api/v2/torrents/add" in calls
