# Maratoncito — Implementation Plan

This plan tracks delivery status and defines the scope, ownership, and acceptance criteria for P0–P4. See [Architecture](ARCHITECTURE.md) for active technical decisions.

## Product goal

Build a self-hosted web application that combines the responsibilities commonly split across Sonarr, Radarr, Bazarr, and Jellyseerr/Overseerr: media discovery, requests, torrent release selection, downloads, library management, automation, and subtitles.

**Main differentiator:** a transparent, flexible release selection engine with reusable language/quality profiles and per-series, per-season, or per-episode release-group preferences.

Maratoncito should be one user-facing application, **not** a rewrite of every infrastructure service. Initially, it delegates indexing to Prowlarr, BitTorrent transfer to qBittorrent, metadata to TMDB/TVDB, and playback to Jellyfin.

## Product principles

1. **One interface and one source of truth** for media items, requests, preferences, and download state.
2. **Deterministic, explainable release selection.** Every acceptance, rejection, and score must be inspectable; no opaque automatic decisions.
3. **Profiles persist and inherit.** Global defaults may be overridden at series, season, and episode level without resetting unrelated fields.
4. **Manual choices inform automation.** Selecting a trusted release group can influence the remaining episodes of a season.
5. **Safe library operations.** Favor hardlinks when supported, do not lose seeding ability, and never silently delete or replace media.
6. **Incremental integrations.** Treat indexers, download clients, metadata providers, and media servers as adapters.
7. **Small self-hosted footprint.** Aim for Docker Compose on Linux/ARM64, including Raspberry Pi 5; keep operational dependencies minimal.

## Functional components

| Component | Responsibility / outcome | Initial priority |
| --- | --- | --- |
| **Catalog & Metadata** | Search movies/series; resolve stable title IDs, seasons, episodes, release dates, alternative titles, and original language via TMDB/TVDB. | MVP |
| **Indexer Integration** | Query multiple trackers via Prowlarr; normalize results and deduplicate mirrored releases. Consider native indexers only later. | MVP |
| **Release Parser** | Extract media type, series/season/episode, resolution, source, codec, languages, release group, and other signals; record unknown values instead of guessing. | MVP |
| **Selection Engine** | Filter and rank normalized releases against constraints, preferences, availability, and explicit overrides; return explanation per candidate. | MVP |
| **Download Manager** | Submit to qBittorrent, reconcile download states, retry safely, and detect completion and failure. | MVP |
| **Library Manager** | Detect existing/missing episodes and files; import and rename releases; create hardlinks on the same filesystem; expose organized media to Jellyfin. | MVP |
| **Profile Manager** | Store quality, audio, subtitle, preferred release-group, and override rules across global/series/season/episode scopes. | MVP |
| **Automation Engine** | Track monitored titles; periodically search missing episodes; retry and optionally upgrade according to policy. | MVP |
| **Requests Manager** | Accept film/show requests in the same web app; support users, deduplication, approval policy, and request-to-library tracking. | Phase 3 |
| **Subtitle Manager** | Inspect embedded tracks; fetch preferred external subtitles; optionally sync subtitles; report unmet preferences. | Phase 3 |
| **Recommendations** | Offer media discovery and personalized suggestions without triggering unwanted downloads. | Later |

**Dependency distinction:** profile data and media preferences belong to Maratoncito. Prowlarr, qBittorrent, and Jellyfin remain separate systems, even if deployed alongside the application.

## Proposed architecture

```text
                         Web UI
               Discover / Requests / Library
                 Profiles / Queue / Settings
                           |
                    HTTP API (Core)
                           |
      +--------------------+--------------------+
      |                    |                    |
  Catalog &           Selection /          Jobs / Worker
  Metadata             Profiles            Automation
      |                    |                    |
    TMDB/TVDB       Prowlarr -> Parser     Download Manager
                           |                    |
                    Ranked candidates        qBittorrent
                                                |
                                        Library / Subtitle
                                                |
                                         Media filesystem
                                                |
                                             Jellyfin

             Local database: SQLite initially
```

Suggested deployment boundary: one web/API process, one background-worker process (which may initially share a container), and one SQLite database. Avoid unnecessary microservices. This is a **proposal**, not a final technology selection.

### Core domain objects

- **MediaItem**: movie or series with provider IDs and metadata.
- **Season / Episode**: episode numbering, air date, monitoring and library status.
- **Profile**: reusable quality, audio, subtitles, and preferred release rules.
- **ProfileOverride**: scoped overrides with inheritance, including an explicit unset/inherit behavior.
- **ReleaseCandidate**: normalized indexer result plus parser confidence and source identity.
- **SelectionDecision**: accepted/rejected, score, matched rules, and explanatory reasons.
- **DownloadJob**: torrent identity, linked media/episodes, client state, and import status.
- **LibraryFile**: actual path, media identity, verified audio/subtitle tracks, and ownership.
- **MediaRequest**: requesting user, target item, requested scope, approval state, and fulfillment.
- **AuditEvent**: user decisions, automation actions, failures, imports, and deletions.

## Key behavior

### 1. Release-group affinity per season

A user manually selects an episode release such as `Example.Show.S02E03.1080p.WEB-DL-GROUP-X` and chooses **Use this group for the remaining season**.

Available modes:

- **Prefer**: reward releases from `GROUP-X`; fall back to other groups when needed.
- **Require**: accept only `GROUP-X`; leave episodes pending if it is unavailable.
- **Custom pattern**: allow an advanced, explicitly configured regex when group parsing is insufficient.

The parser should first normalize the group name. A regex is a fallback, not a reliable replacement for verifying that a result represents the requested episode. Distinguish **release group/uploader identity** from **seeder count** (availability). Show a preview of matches before saving a season-wide rule.

### 2. Hierarchical profiles

```text
Global defaults
    -> Series profile overrides
        -> Season overrides
            -> Episode overrides
```

Example:

- Global: 1080p preferred, original audio required, Spanish subtitles preferred.
- Series: HEVC preferred.
- Season 2: `GROUP-X` preferred.
- Episode 3: manually selected candidate.

Only explicitly set values override inherited settings. The effective profile must be visible to the user and used for both automatic and manual searches.

Treat **required** vs. **preferred** language separately. Release names provide hints, not proof: inspect actual audio/subtitle tracks after download (e.g., with `ffprobe`) and mark unverified requirements for review. Subtitles may be acquired separately if a suitable track is missing.

### 3. Explainable selection

For each candidate, expose:

- Matched media identity and season/episode coverage.
- Accepted/rejected status and rejection reasons.
- Parsed properties and unknown/uncertain fields.
- Matched profile constraints and preference-based scoring.
- Seeder availability and source/indexer information.
- Whether it matches the preferred or required release group.

Keep **hard constraints** separate from **soft ranking**. Evaluate season packs as multi-episode candidates rather than assuming each release contains a single episode. Do not auto-grab a different candidate after a user explicitly selected an exact release without asking or applying an explicit fallback policy.

### 4. Library management

- Compare catalog episodes with existing files to determine missing content.
- Track qBittorrent jobs and import completed video files into stable movie/series paths.
- Prefer hardlinks so media can remain seeding without duplicating bytes; verify download and library directories are on the same filesystem.
- Support manual review when parsing is ambiguous or the downloaded payload contains unexpected episodes.
- Keep deletion and replacement separate, explicit, and auditable.
- Let Jellyfin scan organized folders; optionally request a library refresh through its API later.

### 5. Requests in the same app

Users search TMDB/TVDB, choose a film or series/season, and request it from the catalog. Configurable policy allows automatic approval for trusted users and review for guests. Duplicate requests for the same item/profile/library should share a download workflow. Request status remains visible through import and availability.

## P0–P4 delivery roadmap

| Phase | Outcome | Status |
| --- | --- | --- |
| P0 — Foundation | Shared contracts, API, persistence, web shell, and delivery baseline | Implementation merged in [#3](https://github.com/GastonRAraujo/Maratoncito/pull/3). |
| P1 — Manual search and download | Search, rank, explicitly select, download, and monitor | Implementation merged in [#4](https://github.com/GastonRAraujo/Maratoncito/pull/4). Live-provider and Raspberry Pi validation remain open. |
| P2 — Smart automation | Save preferences, monitor missing media, and safely import completed jobs | Planned. Core MVP milestone. |
| P3 — Unified experience | Fulfill requests through the app and report verified tracks and Jellyfin availability | Planned. |
| P4 — Production readiness | Ship a recoverable, supportable self-hosted release | Planned. Additional providers and discovery are optional. |

### Ownership and integration

The maintainer designates one integration owner and one sub-agent per active lane. Ownership below is by role. The integration owner owns shared contracts, API composition, migration sequencing, merge order, and phase sign-off. The maintainer approves scope changes and release readiness. Each lane owns its stated implementation boundary and focused tests. The QA lane owns cross-lane fixtures and end-to-end evidence.

At phase entry, review schemas, state transitions, error semantics, and fixture examples before branching. Use separate branches and focused PRs. Develop against fixtures or mocked ports until real dependencies are available. Coordinate shared-file edits with the integration owner, who lands contract and migration changes in dependency order and records the gate evidence in the integration PR or linked validation issue. Implementation can overlap where contracts are stable. A phase closes when its acceptance checks pass and the evidence is recorded.

### P0 — Foundation

**Scope and dependencies.** Bootstrap FastAPI/Pydantic contracts and ports, SQLite with Alembic, a web shell, and a reproducible Compose/CI baseline. Boot and health checks require no upstream accounts.

| Sub-agent | Ownership and deliverable |
| --- | --- |
| Architecture | `contracts.py`, `ports.py`, and [architecture decisions](ARCHITECTURE.md). Define domain identity and adapter boundaries before the other lanes branch. |
| Backend and persistence | API scaffold, models, database lifecycle, and reversible initial migration. |
| Frontend | `frontend/` shell and live status display, initially against the status API fixture. |
| Delivery and QA | Compose, Docker image, CI, and contract, HTTP, migration, and persistence checks. |

**Integration gate and acceptance.** Review shared schemas and table ownership. Verify that a clean checkout can migrate, boot, serve health and versioned status, render live status, and retain data across restart. Check reproducible OpenAPI and CI builds. The [P0 workstream record](P0_WORKSTREAMS.md) contains the foundation checklist. PR #3 records nine local tests passing and the Compose configuration was delivered. P1 CI subsequently covered the image build. The target-device smoke and volume persistence checks remain pending and can be run together with P1 hardware validation.

### P1 — Manual search and download

**Scope and dependencies.** Use P0 contracts (`MediaItem`, `EpisodeRef`, `ReleaseCandidate`, `SelectionDecision`, and `DownloadJob`) and externally configured TMDB, Prowlarr, and qBittorrent. Support movies and individual TV episodes. Persistent rules, monitoring, imports, and multi-episode packs are outside this slice.

| Sub-agent | Ownership and deliverable |
| --- | --- |
| Metadata | `integrations/tmdb.py` maps TMDB catalog results to stable media and episode references. |
| Indexer and parser | `integrations/prowlarr.py` and `releases/parser.py` normalize and deduplicate candidates and preserve unknown fields. |
| Selection | `releases/selection.py` ranks fixture candidates deterministically, with rejection and review reasons. |
| Download | `integrations/qbittorrent.py` owns authenticated submission and category-scoped progress. |
| API integration | `api.py` and `services.py` compose providers and issue short-lived opaque candidate IDs. |
| Frontend | `frontend/` exposes search, release comparison, explicit confirmation, and the manual queue. |
| QA | `backend/tests/` covers provider failures and the full HTTP flow with mock adapters. |

**Integration gate and acceptance.** Freeze catalog, candidate, grab, and progress payloads so selection and UI can proceed with fixture data while adapters are built. Verify the browser flow for a movie and an episode, including a rejected candidate, explicit confirmation of an uncertain candidate, the exact chosen release reaching qBittorrent, and visible progress or failure. Confirm server-side candidate URLs and rejection of expired tokens. Run the flow against configured providers and verify Compose health and persistent storage on Raspberry Pi 5 ARM64. The prior handoff reports passing CI for Python 3.12/3.13, Docker build, and JavaScript checks. [P1 progress](P1_PROGRESS.md) tracks the outstanding live checks.

### P2 — Smart automation

**Scope and dependencies.** Build on P1 selection and the download lifecycle. Persist scoped language and quality profiles, per-season release-group affinity, monitored media, job linkage, and import state. Freeze effective-rule semantics, durable job identity and states, and the import boundary before implementation.

| Sub-agent | Ownership and deliverable |
| --- | --- |
| Profiles | Profile persistence and field-level global → series → season → episode inheritance, including explicit clear and inherit behavior. |
| Release affinity | Group normalization, prefer/require rules, bounded custom patterns, and match previews using the shared rule schema. |
| Download lifecycle | Durable media-to-torrent linkage, duplicate prevention, status reconciliation, and restart-safe retries. |
| Library | Missing-content inventory, episode/file matching, safe destination paths, hardlink import, and manual review for ambiguous payloads. |
| Automation | Scheduler, missing-episode workflow, retry/backoff, and explained outcomes. Start against mocked selection and job ports. |
| Frontend | Profile editor, effective-rule and season-affinity previews, monitoring controls, and job/import history. |
| QA | Fixtures for inheritance, concurrent grabs, restarts, wrong-episode matches, and filesystem/import failure. |

**Integration gate and acceptance.** Land the contracts and migrations first, then connect profile resolution and affinity to selection, the scheduler to durable download jobs, and completed jobs to import. From a manual grab, save a previewed season rule and show it applied to a subsequent missing episode. A preferred group allows configured fallback and a required group leaves unmatched episodes pending. Preserve inherited language/quality constraints, defer unsafe or unverified automated choices for review, and show selection reasons. Exercise repeated scheduler runs and restart recovery to prove one logical grab and one import. Confirm the imported path matches the target episode and the hardlink preserves the seeding source on a compatible filesystem. Report unsupported or ambiguous imports without deleting or replacing files. P3 adds actual media-track verification and subtitle fulfillment.

### P3 — Unified experience

**Scope and dependencies.** Build on P2 monitoring, durable jobs, and imported-file events. Agree on request identity and state, authorization roles, and import, track, and availability events before integrating the lanes.

| Sub-agent | Ownership and deliverable |
| --- | --- |
| Users and requests | Authentication, roles, approval policy, request deduplication, and linkage to the monitored item. |
| Media tracks and subtitles | Inspect embedded tracks, report verified or unmet language requirements, and fetch missing preferred subtitles. Subtitle synchronization is optional. |
| Jellyfin | Library refresh adapter and availability reconciliation based on imported media. |
| Frontend | Request submission, approval, fulfillment status, track/subtitle views, and download history. |
| QA | Permission, duplicate request, unavailable provider, and request-to-library scenarios using shared fixtures. |

**Integration gate and acceptance.** Connect approval to P2 monitoring and feed import and availability back to request status. Verify an authorized user can request a movie or show in Maratoncito and see it progress from approval through download and import to confirmed Jellyfin availability. Concurrent equivalent requests share fulfillment. Unauthorized state changes are rejected. Verify track reporting against actual files, subtitle retrieval when a preferred track is missing, and accurate pending or failure states when a provider is unavailable.

### P4 — Production readiness

**Scope and dependencies.** Validate the P3 integrated workflow on supported deployment targets. Operational and security preparation can start once the relevant interfaces stabilize. Release sign-off requires the integrated system.

| Sub-agent | Ownership and deliverable |
| --- | --- |
| Security | Review authentication and authorization, credentials, adapter input, and import path boundaries. Address release-blocking findings. |
| Reliability and QA | Release smoke and end-to-end tests, outage and restart recovery, upgrade compatibility, and duplicate prevention. |
| Observability | Structured logs and operational health signals for provider, job, and import failures. |
| Deployment and recovery | Compose release packaging, Linux and Raspberry Pi 5 ARM64 verification, upgrade/rollback instructions, and a backup/restore exercise. |
| Extensibility (optional) | Additional providers, discovery/recommendations, policy-driven upgrades, and import or migration tools via reviewed adapter contracts. |

**Integration gate and acceptance.** Run the complete workflow on a clean install and after upgrading a previous database. Exercise provider outages, restart recovery, and restore from backup. Verify that diagnosed failures are visible and credentials are absent from logs. Build and run the release image on Linux and Raspberry Pi 5 ARM64, verify persistent data, and record the release evidence and any known limitations. Optional extensions can ship independently after compatibility checks.

## Critical path and next actions

**Shared P0 contracts → P1 release discovery and explained selection → exact grab and verified download lifecycle → P2 durable reconciliation, safe import, and automation → P3 approved request through import, track reporting, and Jellyfin availability → P4 release validation and recovery.**

1. Run P0/P1 Compose and persistence checks on Raspberry Pi 5 ARM64. Run P1 against configured TMDB, Prowlarr, and qBittorrent and record the evidence in the P1 checklist.
2. In parallel, the integration owner can review the P2 rule, durable-job, and import contracts and create fixtures for the independent lanes. Land shared interfaces and migrations before wiring the automation flow.
3. Close P2 when a monitored missing episode is selected, downloaded, and imported under saved rules with restart-safe behavior. Use that integrated flow to validate P3 fulfillment, then apply the P4 release gate.

## Engineering guardrails

- Favor a small, testable core with adapter interfaces for metadata, indexers, download clients, and media libraries.
- Keep release parsing, scoring, and rule inheritance independently unit-testable using fixtures based on real release names.
- Use stable identities and idempotent background jobs; persist intermediate states to recover after restart.
- Protect against path traversal, unsafe torrent payload paths, and accidental deletion. Do not expose qBittorrent's unauthenticated Web UI publicly.
- Track explicit manual selection versus automated ranking so automation cannot silently override user intent.
- Start with SQLite; consider PostgreSQL only if concurrency and operational needs justify it.
- All documentation, code comments, identifiers, configuration descriptions, commit messages, and application copy must be in **English**.

## Open design decisions

- How to infer and validate release group versus uploader identity across trackers.
- Season-pack behavior, preferred resolution fallback, and upgrade policy.
- Default request approval/authentication mechanism.
- Which metrics best represent selection quality and failed-import rates.

These decisions should be captured before each related phase, not assumed to be implemented.
