"""
YouTube recommendations skill.

Entry point:
    get_youtube_videos(query: str) -> list[dict]

If YOUTUBE_API_KEY is set, queries the YouTube Data API v3 for real
video results including titles, thumbnails, channel names, and durations.

If not set, returns 5 placeholder items with search URLs so the frontend
can still render something useful without a YouTube API key.

Return schema per item:
  {title, channel_name, thumbnail_url, duration, video_url, video_id}
"""
from __future__ import annotations

import logging
import os
import re
import urllib.parse
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
_YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YT_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_MAX_RESULTS = 5


def _parse_iso8601_duration(duration_str: str) -> str:
    """
    Convert an ISO 8601 duration string (e.g. ``PT4M13S``) to ``MM:SS``.

    Returns the original string unchanged if parsing fails.
    """
    if not duration_str:
        return "Unknown"
    match = re.match(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration_str,
    )
    if not match:
        return duration_str

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0) + days * 24
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


async def _fetch_real_videos(query: str) -> list[dict]:
    """Query YouTube Data API v3 and return formatted video list."""
    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": _MAX_RESULTS,
        "key": _YOUTUBE_API_KEY,
        "relevanceLanguage": "en",
        "safeSearch": "moderate",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Search for videos
        search_resp = await client.get(_YT_SEARCH_URL, params=search_params)
        search_resp.raise_for_status()
        search_data = search_resp.json()

    items = search_data.get("items", [])
    if not items:
        return []

    video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]

    # 2. Fetch video durations in a single batch request
    duration_map: dict[str, str] = {}
    if video_ids:
        duration_params = {
            "part": "contentDetails",
            "id": ",".join(video_ids),
            "key": _YOUTUBE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            dur_resp = await client.get(_YT_VIDEOS_URL, params=duration_params)
            if dur_resp.status_code == 200:
                for vid in dur_resp.json().get("items", []):
                    vid_id = vid.get("id")
                    raw_dur = vid.get("contentDetails", {}).get("duration", "")
                    if vid_id:
                        duration_map[vid_id] = _parse_iso8601_duration(raw_dur)

    results: list[dict] = []
    for item in items:
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        results.append(
            {
                "title": snippet.get("title", ""),
                "channel_name": snippet.get("channelTitle", "YouTube"),
                "thumbnail_url": thumbnail_url,
                "duration": duration_map.get(video_id, "Unknown"),
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "video_id": video_id,
            }
        )

    logger.info("YouTube API returned %d videos for query='%s'", len(results), query)
    return results


def _fallback_videos(query: str) -> list[dict]:
    """Return placeholder video items with YouTube search URLs."""
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
    return [
        {
            "title": f"{query} - cooking video {i + 1}",
            "channel_name": "YouTube",
            "thumbnail_url": None,
            "duration": None,
            "video_url": search_url,
            "video_id": None,
        }
        for i in range(_MAX_RESULTS)
    ]


async def get_youtube_videos(query: str) -> list[dict]:
    """
    Return up to 5 YouTube video recommendations for *query*.

    Uses the YouTube Data API v3 when ``YOUTUBE_API_KEY`` is available;
    otherwise returns search-URL placeholders.

    Args:
        query: Search query string, e.g. ``"chicken tikka masala recipe"``.

    Returns:
        List of dicts, each with: title, channel_name, thumbnail_url,
        duration, video_url, video_id.  Never raises — returns an empty
        list or fallback items on any error.
    """
    if not _YOUTUBE_API_KEY:
        logger.info("YOUTUBE_API_KEY not set — returning fallback search URLs.")
        return _fallback_videos(query)

    try:
        return await _fetch_real_videos(query)
    except Exception as exc:
        logger.warning(
            "YouTube API request failed for query='%s': %s — returning fallbacks.",
            query,
            exc,
        )
        return _fallback_videos(query)
