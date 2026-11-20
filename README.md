# Maratoncito

A self-hosted web app for requesting, searching, and downloading movies and TV shows via torrents, with audio/subtitle profiles and preferred release groups per season.

The goal is to bring Sonarr, Radarr, Bazarr, and Jellyseerr/Overseerr workflows into one interface while initially relying on Prowlarr for indexers and qBittorrent for downloads.

## Project status

Maratoncito is in its initial scaffolding stage. The current service exposes a health-check endpoint only. Media catalog, discovery, downloads, automation, and request management are planned, not yet implemented.

See the [implementation plan](docs/IMPLEMENTATION_PLAN.md) for component responsibilities, architecture, and delivery phases.

## Local setup

Requires Docker with the Compose plugin. From a Raspberry Pi or another development machine:

```sh
cp .env.example .env
docker compose up --build -d
curl --fail http://127.0.0.1:8000/health
```

Expected response: `{"status":"ok"}`.

The service binds to localhost by default. To access it from another device on your LAN, configure `MARATONCITO_BIND_HOST` in `.env` to your host's LAN IP address. Set `MARATONCITO_PORT` if port 8000 is already in use. Do not expose the development endpoint directly to the internet.

To stop the service:

```sh
docker compose down
```

## License

MIT. See [LICENSE](LICENSE).
