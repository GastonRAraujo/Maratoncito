"""Conservative filename-based release parsing.

These are hints, not verified media tracks. P2/P3 will verify tracks with ffprobe.
"""

import re

from maratoncito.contracts import ParsedRelease

_EPISODE = re.compile(r"(?<![A-Za-z0-9])S(\d{1,2})E(\d{1,3})(?:-?E?(\d{1,3}))?(?!\d)", re.I)
_SEASON = re.compile(r"(?<![A-Za-z0-9])S(\d{1,2})(?![A-Za-z0-9])", re.I)
_GROUP = re.compile(r"-([A-Za-z0-9][A-Za-z0-9._]{1,39})$", re.I)


def parse_release(title: str) -> ParsedRelease:
    cleaned = title.replace(".", " ").replace("_", " ")
    episode_match = _EPISODE.search(cleaned)
    season_match = _SEASON.search(cleaned)
    resolution = next((r for r in ("2160p", "1080p", "720p", "480p") if re.search(rf"\b{r}\b", cleaned, re.I)), None)
    source = next(
        (label for expression, label in (
            (r"WEB[ .-]?DL", "WEB-DL"),
            (r"WEB[ .-]?Rip", "WEBRip"),
            (r"Blu[ .-]?Ray|BDRip|BRRip", "BluRay"),
            (r"HDTV", "HDTV"),
            (r"DVD", "DVD"),
        ) if re.search(expression, cleaned, re.I)),
        None,
    )
    codec = next(
        (label for expression, label in (
            (r"\b(?:x265|h265|hevc)\b", "HEVC"),
            (r"\b(?:x264|h264|avc)\b", "H264"),
            (r"\bav1\b", "AV1"),
        ) if re.search(expression, cleaned, re.I)),
        None,
    )

    # Only explicit filename language markers are hints; 'DUAL' is not an ISO language.
    languages = []
    for expression, iso in ((r"\b(?:SPANISH|CASTELLANO|LATINO|ESP)\b", "es"),
                            (r"\b(?:ENGLISH|ENG)\b", "en"),
                            (r"\b(?:FRENCH|FRE)\b", "fr"),
                            (r"\b(?:JAPANESE|JPN)\b", "ja")):
        if re.search(expression, cleaned, re.I):
            languages.append(iso)

    group_match = _GROUP.search(title)
    if episode_match:
        first = int(episode_match.group(2))
        last = int(episode_match.group(3)) if episode_match.group(3) else first
        episodes = list(range(first, min(last, first + 40) + 1)) if last >= first else [first]
        kind = "episode"
        season = int(episode_match.group(1))
    elif season_match:
        kind, season, episodes = "season_pack", int(season_match.group(1)), []
    else:
        kind, season, episodes = "movie", None, []

    return ParsedRelease(
        kind=kind,
        season_number=season,
        episode_numbers=episodes,
        resolution=resolution,
        source=source,
        codec=codec,
        release_group=group_match.group(1) if group_match else None,
        audio_languages=languages,
        confidence=0.7 if resolution and (episode_match or season_match) else 0.4,
    )
