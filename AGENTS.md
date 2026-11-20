# Repository Guidelines

- **English only** for repository documentation, code comments, identifiers, configuration descriptions, commit and PR text, and user-facing application copy.
- Use [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the roadmap and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for active decisions.
- Follow ownership boundaries and integration gates in [docs/P0_WORKSTREAMS.md](docs/P0_WORKSTREAMS.md); don't edit another lane's modules without coordinating changes.
- Treat `backend/maratoncito/contracts.py` and `ports.py` as shared interfaces. Review changes before parallel feature development.
- Selection logic must be deterministic and testable without HTTP, torrent clients or indexers.
- Keep integrations behind ports. Preserve explicit user choices and never imply a verified audio track from a torrent filename.
- Use Alembic migrations; do not call `create_all` on startup.
- Every PR needs tests or a justification. Document actual validation; do not claim ARM64 support without testing.
- Favor small, reversible changes. Avoid extra services unless necessary.
