# Maratoncito

A self-hosted web app for requesting, searching, and downloading movies and TV shows via torrents, with audio/subtitle profiles and preferred release groups per season.

The goal is to combine Sonarr, Radarr, Bazarr, and Jellyseerr/Overseerr workflows in one interface, initially using Prowlarr for indexers and qBittorrent for downloads.

## Current status

**P1 manual search and download development.** The web UI allows TMDB media search, Prowlarr release discovery with explicit selection reasons, and manual qBittorrent torrent submission and progress (when external services are configured).

Automatic monitoring, persistent profile rules, audio/subtitle verification, file import, and user requests are **not yet implemented**.

- [Implementation roadmap](docs/IMPLEMENTATION_PLAN.md)
- [P1 status and limitations](docs/P1_PROGRESS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Agent ownership](docs/P0_WORKSTREAMS.md)

## Run with Docker Compose

The application needs existing **Prowlarr** and **qBittorrent** instances, plus a TMDB API key. Prowlarr aggregates tracker searches; qBittorrent transfers the selected torrents.

```sh
cp .env.example .env
# Edit .env with TMDB_API_KEY, PROWLARR_API_KEY, and qBittorrent connection values.
docker compose up --build -d
curl --fail http://127.0.0.1:8000/health
```

Open `http://127.0.0.1:8000`, search a title, choose a movie or an individual TV episode, and inspect release scores before downloading. `/docs` contains the OpenAPI reference.

The Docker Compose network resolves `host.docker.internal` to the host gateway on Linux. Prowlarr and qBittorrent must listen on addresses reachable from that gateway, not only on the host's loopback interface. **Use qBittorrent credentials**, and make sure qBittorrent can resolve the download links returned by Prowlarr. Neither provider is added as a Compose service by default.

The application itself has no login mechanism. **Do not expose its port to the public internet.** The `MARATONCITO_BIND_HOST` default remains `127.0.0.1`.

```sh
docker compose down
```

## Backend development

Python 3.12+:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
python -m alembic upgrade head
uvicorn maratoncito.main:app --reload
```

Test from the repository root:

```sh
python -m pytest -q backend/tests
python scripts/export_openapi.py --check
```

## License

MIT. See [LICENSE](LICENSE).
