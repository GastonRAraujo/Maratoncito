"""Pure, deterministic release ranking and rejection explanations."""

import math
import re
from collections.abc import Sequence

from maratoncito.contracts import (
    EpisodeRef, MediaItem, ProfileRules, ReleaseCandidate, SelectionDecision,
)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def _group_matches(pattern: str, group: str | None) -> bool:
    return group is not None and group.casefold() == pattern.casefold()


def score_candidate(
    candidate: ReleaseCandidate,
    media: MediaItem,
    episode: EpisodeRef | None,
    profile: ProfileRules,
) -> SelectionDecision:
    reasons: list[str] = []
    rejected = False
    review = False
    parsed = candidate.parsed
    title_words = _tokens(candidate.title)
    media_words = _tokens(media.title)
    if not media_words or not all(word in title_words for word in media_words):
        rejected = True
        reasons.append("Release title does not match the requested media")

    if media.kind == "series":
        if episode is None:
            rejected = True
            reasons.append("An episode must be specified for series searches")
        elif parsed.kind != "episode":
            rejected = True
            reasons.append("Not an individual episode release (season packs are not supported in P1)")
        elif parsed.season_number != episode.season_number or episode.episode_number not in parsed.episode_numbers:
            rejected = True
            reasons.append("Wrong season or episode")
    elif parsed.kind in {"episode", "season_pack"}:
        rejected = True
        reasons.append("TV release does not match a movie")
    elif media.year and (year_tokens := re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", candidate.title)):
        if str(media.year) not in year_tokens:
            rejected = True
            reasons.append("Release year does not match the requested movie")

    score = 0.0
    if not parsed.resolution:
        review = True
        reasons.append("Resolution could not be verified from the title")
    elif parsed.resolution not in profile.resolutions:
        rejected = True
        reasons.append(f"Resolution {parsed.resolution} is outside the profile")
    else:
        score += (len(profile.resolutions) - profile.resolutions.index(parsed.resolution)) * 20

    group_policy = profile.release_group
    if group_policy.mode == "require" and not _group_matches(group_policy.value or "", parsed.release_group):
        rejected = True
        reasons.append("Required release group not found")
    elif group_policy.mode == "prefer" and _group_matches(group_policy.value or "", parsed.release_group):
        score += 50
        reasons.append("Preferred release group matched")
    elif group_policy.mode == "regex":
        rejected = True
        reasons.append("Custom regex groups are not supported until P2")

    if profile.audio_mode == "original" and media.original_language:
        # Filenames cannot reliably prove audio languages. Treat apparent mismatches as reviewable.
        if parsed.audio_languages and media.original_language not in parsed.audio_languages:
            review = True
            reasons.append("Original audio is not confirmed by filename hints")
        elif not parsed.audio_languages:
            review = True
            reasons.append("Audio language must be verified after download")
    elif profile.audio_mode == "prefer" and profile.preferred_audio_languages:
        if any(language in parsed.audio_languages for language in profile.preferred_audio_languages):
            score += 10
        else:
            reasons.append("Preferred audio not confirmed by filename")

    if candidate.seeders is None:
        reasons.append("Seeder count unavailable")
    elif candidate.seeders == 0:
        review = True
        reasons.append("No available seeders reported")
    else:
        score += min(30.0, 5 * math.log2(candidate.seeders + 1))

    if parsed.codec == "HEVC":
        score += 5

    outcome = "rejected" if rejected else "needs_review" if review else "accepted"
    if not reasons:
        reasons.append("Matches the requested media and quality profile")
    return SelectionDecision(
        candidate_id=candidate.id,
        outcome=outcome,
        score=round(score, 2) if not rejected else None,
        reasons=reasons,
    )


def rank_releases(
    candidates: Sequence[ReleaseCandidate],
    media: MediaItem,
    episode: EpisodeRef | None,
    profile: ProfileRules,
) -> list[SelectionDecision]:
    decisions = [score_candidate(candidate, media, episode, profile) for candidate in candidates]
    priority = {"accepted": 0, "needs_review": 1, "rejected": 2}
    return sorted(decisions, key=lambda item: (priority[item.outcome], -(item.score or 0), item.candidate_id))
