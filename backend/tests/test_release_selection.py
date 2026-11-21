from maratoncito.contracts import EpisodeRef, MediaItem, ProfileRules, ReleaseCandidate, ReleaseGroupPolicy
from maratoncito.releases.parser import parse_release
from maratoncito.releases.selection import rank_releases, score_candidate


def candidate(title: str, seeders: int = 20) -> ReleaseCandidate:
    return ReleaseCandidate(
        id=title, title=title, indexer="test", seeders=seeders, parsed=parse_release(title)
    )


def test_parser_extracts_episode_group_and_codec() -> None:
    parsed = parse_release("Example.Show.S02E03.1080p.WEB-DL.x265-GROUPX")
    assert parsed.kind == "episode"
    assert parsed.season_number == 2
    assert parsed.episode_numbers == [3]
    assert parsed.release_group == "GROUPX"
    assert parsed.codec == "HEVC"


def test_parser_season_pack_is_not_episode() -> None:
    parsed = parse_release("Example.Show.S02.1080p.WEB-DL-PACKTEAM")
    assert parsed.kind == "season_pack"


def test_wrong_episode_is_rejected() -> None:
    media = MediaItem(id="tmdb:tv:1", kind="series", title="Example Show")
    episode = EpisodeRef(series_id=media.id, season_number=2, episode_number=4)
    decision = score_candidate(candidate("Example.Show.S02E03.1080p.WEB-DL-GROUPX"), media, episode, ProfileRules())
    assert decision.outcome == "rejected"
    assert any("Wrong season or episode" in reason for reason in decision.reasons)


def test_required_group_rejects_other_groups() -> None:
    media = MediaItem(id="tmdb:movie:1", kind="movie", title="Example Film")
    profile = ProfileRules(release_group=ReleaseGroupPolicy(mode="require", value="GROUPX"))
    decision = score_candidate(candidate("Example.Film.2024.1080p.WEB-DL-OTHER"), media, None, profile)
    assert decision.outcome == "rejected"


def test_preferred_group_wins_over_extra_seeders() -> None:
    media = MediaItem(id="tmdb:movie:1", kind="movie", title="Example Film")
    profile = ProfileRules(release_group=ReleaseGroupPolicy(mode="prefer", value="GROUPX"))
    a = candidate("Example.Film.2024.1080p.WEB-DL-GROUPX", seeders=10)
    b = candidate("Example.Film.2024.1080p.WEB-DL-OTHER", seeders=40)
    result = rank_releases([b, a], media, None, profile)
    assert result[0].candidate_id == a.id


def test_unknown_audio_requires_review_not_false_verification() -> None:
    media = MediaItem(id="tmdb:movie:2", kind="movie", title="Example Film", original_language="en")
    decision = score_candidate(candidate("Example.Film.2024.1080p.WEB-DL-GROUPX"), media, None, ProfileRules())
    assert decision.outcome == "needs_review"
    assert any("verified" in reason for reason in decision.reasons)


def test_movie_year_mismatch_rejected() -> None:
    media = MediaItem(id="tmdb:movie:2", kind="movie", title="Example Film", year=2024)
    decision = score_candidate(candidate("Example.Film.2001.1080p.WEB-DL-GROUPX"), media, None, ProfileRules())
    assert decision.outcome == "rejected"
