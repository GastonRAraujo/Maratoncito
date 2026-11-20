# P0 — Agent Workstreams and Integration Plan

**Status:** Initial foundation implementation. These are independent ownership boundaries suitable for Codex sub-agents. This document does **not** claim agents have run.

## Dependency gate

Shared contracts in `contracts.py`, `ports.py` and `docs/ARCHITECTURE.md` are reviewed before feature work branches. No agent should modify shared domain models or persistent tables without coordinating with the integration owner.

| Lane | Ownership | Scope | Integration check |
| --- | --- | --- | --- |
| A — Architecture | `docs/ARCHITECTURE.md`, `contracts.py`, `ports.py` | Domain and API models, ports, interface changes | Contract and OpenAPI tests |
| B — Backend & Persistence | `backend/maratoncito/db.py`, `models.py`, `backend/alembic/` | Persistence, migration lifecycle, API implementation | Upgrade/downgrade and HTTP tests |
| C — Frontend | `frontend/` | Shell, status view, future feature UI | Browser renders live API status |
| D — Delivery & QA | `Dockerfile`, `compose.yaml`, `.github/`, `backend/tests/`, `scripts/` | CI, image, tests and smoke checks | CI and Compose build succeed |

## Parallel sub-agent rules

1. **One owner per path.** Cross-lane changes require a small shared-contract PR or integration-owner review.
2. **Independent branches and PRs.** Each workstream should include its tests and acceptance criteria.
3. **Mock dependency ports.** Agents can work against interfaces while TMDB, Prowlarr, and qBittorrent adapters are developed independently.
4. **Integration gates.** A dedicated integration owner reviews cross-lane API assumptions, migrations, and merge order.
5. **Evidence-based completion.** Do not claim Docker or ARM64 support without building and running the resulting container.
6. **English only** in all repository artifacts and user-facing application strings.

## P0 acceptance checklist

- [x] Architecture and module ownership documented.
- [x] Core Pydantic contracts and integration ports scaffolded.
- [x] Versioned FastAPI status endpoint.
- [x] SQLite models and reversible Alembic initial migration.
- [x] Minimal web shell consumes the real status API.
- [x] Compose and CI configuration added.
- [ ] GitHub Actions CI confirmed green on the PR.
- [ ] Container verified on Raspberry Pi 5 (ARM64) with persistent data.

## Next parallel assignments for P1

- **Metadata agent:** TMDB search/lookup behind `MetadataProvider` and fixtures; own `metadata/`.
- **Indexer/parser agent:** Prowlarr search, deduplication, release normalization; own `indexers/` and `parser/`.
- **Selection agent:** pure deterministic ranking using `ProfileRules` and `SelectionDecision` with real-title fixtures; own `selection/`.
- **Download agent:** qBittorrent integration, idempotent enqueue and state reconciliation; own `downloads/`.
- **UI agent:** media discovery, ranked candidate details, download queue; own `frontend/`.
- **Integration owner:** API contract review, end-to-end tests, merge order and Docker Compose smoke tests.
