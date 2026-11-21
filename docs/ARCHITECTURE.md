# P0 Architecture Decision Record

**Status:** Accepted for the foundation; revisit only when a concrete requirement justifies change.

## Runtime and boundaries

- **API:** Python 3.13, FastAPI and Pydantic v2. Routes under `/api/v1`; `/health` is intentionally stable.
- **Persistence:** SQLite with SQLAlchemy 2 and Alembic migrations; one database volume. Never call ORM `create_all()` on startup.
- **Web shell:** dependency-free HTML, CSS and JavaScript served by FastAPI. This is intentionally a minimal shell rather than a permanent frontend framework decision.
- **Deployment:** one Docker Compose service on Linux and ARM64-targeted hosts, one persistent named volume. Prowlarr and qBittorrent are **not required** for the P0 boot.
- **Module ownership:** shared contracts and ports live in `backend/maratoncito/`; future metadata, indexer, parser, selection, downloads, library, and automation implementations each own separate modules.

## Integration topology

```text
Browser (frontend/) --> FastAPI (/api/v1) --> Application services (future)
                           |                     |         |
                           |                  Prowlarr  qBittorrent (future)
                           +--> SQLAlchemy / SQLite (Alembic)
                           +--> TMDB / TVDB (future)

Organized media --> Jellyfin (future)
```

## Contract rules

1. Shared Pydantic models live in `backend/maratoncito/contracts.py` and external integration interfaces in `ports.py`.
2. Contract changes need review before multiple independent agents implement against them. FastAPI generates the OpenAPI schema; CI checks its generation.
3. Release group/uploader identity and seeder count are different concepts. Do not confuse them.
4. Unknown release metadata remains unknown; never fabricate release-language or parsing confidence.
5. Selection acceptance/rejection reasons and scores must be explicit and reproducible.
6. The current `ProfileOverride` omits inherited fields. Explicit clearing semantics and inheritance implementation remain P2 design work.
7. Each persistence change requires an Alembic migration.

## Database ownership

- `media_items`: stable provider-linked catalog identity.
- `download_jobs`: durable association between a selected release candidate and a media item; torrent integration is not present yet.
- `profiles`: persistence placeholders for scoped overrides; P0 does not resolve profiles.

These tables are initial scaffolding only; domain agents must review constraints and add migrations before using them.

## P0 limitations

`/api/v1/system/status` accurately reports all product capabilities as unavailable. No torrent searching, download management, requests, or library mutations are implemented in this phase.
