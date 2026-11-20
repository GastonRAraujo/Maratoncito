# Repository Guidelines

- **English only** for repository documentation, README files, code comments, variable/function names, configuration descriptions, commit and pull request text, and user-facing application copy.
- Use [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) as the current product and architectural roadmap. Planned features are not implemented features.
- Keep the selection engine independent of the UI, torrent clients, and indexers so it can be unit-tested with release fixtures.
- Prefer small, testable increments. Do not introduce additional runtime services without an explicit need.
- Preserve user selection intent, validate downloaded tracks rather than trusting names alone, and avoid destructive operations without explicit safeguards.
