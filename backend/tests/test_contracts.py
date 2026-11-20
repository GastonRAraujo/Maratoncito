import pytest
from pydantic import ValidationError

from maratoncito.contracts import (
    ParsedRelease,
    ProfileOverride,
    ReleaseCandidate,
    ReleaseGroupPolicy,
    SelectionDecision,
)


def test_parser_distinguishes_group_from_seeders() -> None:
    candidate = ReleaseCandidate(
        id="indexer:1",
        indexer="example",
        title="Example.Show.S02E03.1080p.WEB-DL-GROUP-X",
        seeders=18,
        parsed=ParsedRelease(kind="episode", season_number=2, episode_numbers=[3], release_group="GROUP-X"),
    )
    assert candidate.seeders == 18
    assert candidate.parsed.release_group == "GROUP-X"


def test_explanations_have_explicit_outcomes() -> None:
    decision = SelectionDecision(candidate_id="x", outcome="rejected", reasons=["Wrong episode"])
    assert decision.score is None
    assert decision.reasons == ["Wrong episode"]


def test_group_requires_value() -> None:
    with pytest.raises(ValidationError):
        ReleaseGroupPolicy(mode="require")


def test_empty_override_inherits_everything() -> None:
    override = ProfileOverride()
    assert override.model_dump(exclude_unset=True) == {}
    override = ProfileOverride(subtitle_languages=["es"])
    assert override.model_dump(exclude_unset=True) == {"subtitle_languages": ["es"]}
