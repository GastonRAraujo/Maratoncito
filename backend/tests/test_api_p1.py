from fastapi.testclient import TestClient

from maratoncito.contracts import EpisodeRef, MediaItem, ReleaseCandidate
from maratoncito.integrations.prowlarr import IndexerHit
from maratoncito.integrations.qbittorrent import TorrentProgress
from maratoncito.main import app
from maratoncito.releases.parser import parse_release
from maratoncito.services import P1Service, get_service


class FakeIndexer:
    async def search(self, media, episode):
        return [
            IndexerHit(
                candidate=ReleaseCandidate(
                    id="internal-id", title="Example.Show.S02E03.1080p.WEB-DL-GROUPX",
                    indexer="fake", seeders=20,
                    parsed=parse_release("Example.Show.S02E03.1080p.WEB-DL-GROUPX"),
                ),
                download_url="magnet:?xt=urn:btih:FAKE",
            )
        ]


class FakeDownloader:
    def __init__(self):
        self.added = []

    async def add(self, download_url, candidate_id):
        self.added.append((download_url, candidate_id))

    async def list(self):
        return [TorrentProgress(hash="fake", name="Example Show", state="downloading", progress=0.2, size_bytes=1000)]


def test_search_preview_and_explicit_grab() -> None:
    fake_downloader = FakeDownloader()
    service = P1Service()
    service.indexer = lambda: FakeIndexer()
    service.downloader = lambda: fake_downloader
    app.dependency_overrides[get_service] = lambda: service

    media = MediaItem(id="tmdb:tv:1", kind="series", title="Example Show", original_language="en")
    episode = EpisodeRef(series_id=media.id, season_number=2, episode_number=3)
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/releases/search", json={"media": media.model_dump(), "episode": episode.model_dump()})
            assert response.status_code == 200
            result = response.json()[0]
            assert result["decision"]["outcome"] == "needs_review"
            assert "download_url" not in str(result)
            token = result["candidate"]["id"]
            assert client.post("/api/v1/downloads", json={"candidate_id": token}).status_code == 409
            assert not fake_downloader.added
            accepted = client.post("/api/v1/downloads", json={"candidate_id": token, "confirm_unverified": True})
            assert accepted.status_code == 200
            assert accepted.json()["status"] == "submitted"
            assert fake_downloader.added[0][0].startswith("magnet:")
            queue = client.get("/api/v1/downloads")
            assert queue.json()[0]["progress"] == 0.2
    finally:
        app.dependency_overrides.clear()


def test_episode_must_match_selected_series() -> None:
    with TestClient(app) as client:
        media = MediaItem(id="tmdb:tv:1", kind="series", title="Example Show")
        body = {"media": media.model_dump(), "episode": {"series_id": "wrong", "season_number": 2, "episode_number": 3}}
        assert client.post("/api/v1/releases/search", json=body).status_code == 422


def test_missing_candidate_is_not_a_url_passthrough() -> None:
    with TestClient(app) as client:
        result = client.post("/api/v1/downloads", json={"candidate_id": "https://example.com/torrent"})
        assert result.status_code == 409
