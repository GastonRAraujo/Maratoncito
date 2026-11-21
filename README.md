# Maratoncito

A self-hosted web app for requesting, searching, and downloading movies and TV shows via torrents, with audio/subtitle profiles and preferred release groups per season.

The goal is to combine Sonarr, Radarr, Bazarr, and Jellyseerr/Overseerr workflows in one interface, initially using Prowlarr for indexers and qBittorrent for downloads.

## Status

**P0 foundation only.** The web page shows backend status; the API exposes `/health` and `/api/v1/system/status`. Media search, downloads, profiles, and requests are not implemented yet.

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture and contracts](docs/ARCHITECTURE.md)
- [P0 agent workstreams](docs/P0_WORKSTREAMS.md)

## Quick start (Docker Compose)

```sh
cp .env.example .env
docker compose up --build -d
curl --fail http://127.0.0.1:8000/health
```

Open `http://127.0.0.1:8000` to view the shell. Expected health response: `{"status":"ok"}`. Container startup applies checked-in Alembic migrations to a persistent SQLite volume.

By default, the service listens on localhost. To access it from another device on your LAN, set `MARATONCITO_BIND_HOST` in `.env` to the host LAN IP. Set `MARATONCITO_PORT` to change the port; do not expose the development service directly to the internet.

```sh
docker compose down
```

## Backend development

Requires Python 3.12+:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
python -m alembic upgrade head
uvicorn maratoncito.main:app --reload
```

Run tests from the repository root:

```sh
python -m pytest -q backend/tests
python scripts/export_openapi.py --check
```

Interactive OpenAPI docs are available at `/docs` while the API runs.

## License

MIT. See [LICENSE](LICENSE).
