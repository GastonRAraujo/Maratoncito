# P1 — Manual Media Discovery and Torrent Downloads

**Status:** The first end-to-end implementation merged in [PR #4](https://github.com/GastonRAraujo/Maratoncito/pull/4). Live-provider and Raspberry Pi 5 ARM64 validation remain pending. See the [P0–P4 roadmap](IMPLEMENTATION_PLAN.md) for the phase gates.

## Implemented workstreams

| Agent lane | Owner directories | Result |
| --- | --- | --- |
| Metadata | `backend/maratoncito/integrations/tmdb.py` | TMDB movie and series search, normalized to `MediaItem` |
| Indexer + parser | `integrations/prowlarr.py`, `releases/parser.py` | Prowlarr search, conservative title parsing, deduplication and source identity |
| Selection | `releases/selection.py` | Deterministic filtering, scoring, rejected/reviewed/accepted decisions with reasons |
| Download client | `integrations/qbittorrent.py` | Authenticated torrent submission and category-filtered progress |
| API + orchestration | `api.py`, `services.py` | Search/grab endpoints, transient opaque selection tokens |
| UI | `frontend/` | Movie and episode selection, release comparison and manual download queue |
| Quality / integration | `backend/tests/`, `.github/workflows/` | Mock upstream integration tests and CI |

Each lane is intentionally independently testable. All cross-component behavior is exercised through the HTTP API.

## HTTP routes

- `GET /api/v1/catalog/search?q=<title>&kind=all|movie|series` — search TMDB.
- `POST /api/v1/releases/search` — supply `{ "media": MediaItem, "episode": EpisodeRef|null, "profile": ProfileRules }`; returns candidates and selection decisions.
- `POST /api/v1/downloads` — supply `{ "candidate_id": "<opaque token>", "confirm_unverified": true|false }`; submit **exactly the selected candidate**.
- `GET /api/v1/downloads` — list torrents under the dedicated `maratoncito` category in qBittorrent.
- `GET /api/v1/system/status` — available and unimplemented capabilities.

Release search requires a specific episode for TV; season packs are rejected until multi-episode import is designed.

## Security and workflow decisions

1. **No user-supplied torrent URL is accepted by the grab endpoint.** A short-lived, opaque, in-memory token references a previously searched release. Tokens expire after 15 minutes or on restart.
2. **Reject vs. review matters.** A rejected candidate cannot be grabbed. A candidate with unverified filename metadata requires an explicit confirmation.
3. **Unknown audio is not proof of an audio match.** Language/subtitle track verification and subtitle downloads belong to later phases.
4. **No automatic downloads.** Search and grab require an explicit user action. Monitoring, import, persistent library state and upgrades remain P2.
5. **Application is not authenticated.** Keep port bound to localhost by default. Do not expose the HTTP API to untrusted networks without access control.
6. **qBittorrent must be network-reachable from the container.** Configure Web UI credentials; Docker gateway traffic does not qualify for localhost authentication bypass.
7. **Prowlarr release URLs must be reachable by qBittorrent.** If Prowlarr advertises a private hostname the qBittorrent container cannot resolve, downloads will fail.
8. **No separate Prowlarr or qBittorrent containers are forced by this Compose file.** Integrations are configured against an existing installation.

## P1 limitations and next steps

- **Selection tokens are not persisted:** after an API restart or token expiry, search again. qBittorrent retains accepted torrents.
- **No persistent media-job linkage:** the current download queue is qBittorrent's category-filtered list; profile context is not stored with torrents yet.
- **Release parsing is conservative** and cannot reliably infer original audio, subtitle tracks, unusual numbering, uploader aliases or season packs.
- **Regex group preferences, season affinity, persistent profile overrides and import to Jellyfin are P2 work.**
- **No authentication or multi-user request workflow (P3).**

## P1 acceptance checks

- [x] Code for catalog search, Prowlarr search, parsing and explained ranking.
- [x] Code for exact manual grab and qBittorrent category progress.
- [x] Web UI surfaces these workflows.
- [x] Mock TMDB, Prowlarr and qBittorrent tests added.
- [x] PR CI reported passing in the implementation handoff, including image build.
- [ ] Tested manually with real TMDB, Prowlarr and qBittorrent credentials.
- [ ] Raspberry Pi 5 ARM64 smoke test.
