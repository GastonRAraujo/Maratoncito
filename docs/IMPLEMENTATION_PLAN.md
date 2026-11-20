# Maratoncito — Implementation Plan

Status: **proposed architecture and phased roadmap**. This document describes intended behavior, not features already implemented.

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

## Implementation phases

### Phase 1 — Manual search and download (first vertical slice)

**Scope:** minimal web UI/API, catalog search, Prowlarr integration, release parser, selection explanations, and qBittorrent integration.

**Acceptance criteria:**

- Search a film or a specific TV episode.
- See deduplicated release candidates with parsed attributes and clear rejection reasons.
- Select one exact candidate and send it to qBittorrent.
- View basic download progress and failures.
- Run the application via Docker Compose on Linux/ARM64.

### Phase 2 — Profiles, library, and automation

**Scope:** hierarchical profiles; original-audio / subtitle preferences; preferred/required release group per season; background monitoring; missing-episode detection; hardlink import and safe retry behavior.

**Acceptance criteria:**

- Selecting a release group for an episode can apply a saved rule to the rest of the season, with a preview and fallback policy.
- Existing and new episodes use the correct effective profile.
- Completed downloads import into the correct library paths without duplicate media bytes on a compatible filesystem.
- A background job finds and processes monitored missing episodes without duplicate grabs.
- User can inspect why automation accepted, rejected, or deferred a release.

### Phase 3 — Requests, users, and subtitles

**Scope:** integrated requests UI and approval rules, multiple users, media-track validation, external subtitles, optional subtitle sync, and Jellyfin coordination.

**Acceptance criteria:**

- Users submit requests without a separate Overseerr/Jellyseerr instance.
- An approved request becomes a monitored item with progress visible in the app.
- Audio/subtitle preferences survive across episodes and are checked against downloaded files.
- Existing requests and downloads are not duplicated.

### Phase 4 — Discovery and extensibility (optional)

Recommendation/discovery features, more download and indexer adapters, smarter upgrades, import/migration tools, and operational improvements.

## Engineering guardrails

- Favor a small, testable core with adapter interfaces for metadata, indexers, download clients, and media libraries.
- Keep release parsing, scoring, and rule inheritance independently unit-testable using fixtures based on real release names.
- Use stable identities and idempotent background jobs; persist intermediate states to recover after restart.
- Protect against path traversal, unsafe torrent payload paths, and accidental deletion. Do not expose qBittorrent's unauthenticated Web UI publicly.
- Track explicit manual selection versus automated ranking so automation cannot silently override user intent.
- Start with SQLite; consider PostgreSQL only if concurrency and operational needs justify it.
- All documentation, code comments, identifiers, configuration descriptions, commit messages, and application copy must be in **English**.

## Open design decisions

- Final backend/frontend technology choice (the existing Python health endpoint is only scaffolding).
- How to infer and validate release group versus uploader identity across trackers.
- Season-pack behavior, preferred resolution fallback, and upgrade policy.
- Default request approval/authentication mechanism.
- Whether subtitles are bundled into the initial MVP or shipped in Phase 3.
- Which metrics best represent selection quality and failed-import rates.

These decisions should be captured before each related phase, not assumed to be implemented.
