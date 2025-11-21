"""YouTube search functionality using Google API."""
import os
import html
import json
import logging
import subprocess
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from mock_data import MOCK_SEARCH_RESULTS
from cache import SearchCache

logger = logging.getLogger(__name__)


class YouTubeSearcher:
    """Handle YouTube searches using the official API."""

    def __init__(self, api_key: str | None = None, mock_mode: bool = False):
        """Initialize the YouTube searcher.

        Args:
            api_key: YouTube Data API v3 key. If None, reads from YOUTUBE_API_KEY env var.
            mock_mode: If True, use mock data instead of calling the real API (for development).
        """
        self.mock_mode = mock_mode
        self.cache = SearchCache()  # 24-hour TTL by default

        if not mock_mode:
            self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
            if not self.api_key:
                raise ValueError("YouTube API key not provided and YOUTUBE_API_KEY env var not set")

            self.youtube = build("youtube", "v3", developerKey=self.api_key)
        else:
            logger.info("Mock mode enabled - using fake search results")
            self.api_key = None
            self.youtube = None

    def ytdlp_search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search using yt-dlp as fallback when API is unavailable.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of search result dictionaries (same format as official API)
        """
        try:
            logger.info(f"Using yt-dlp search for: '{query}' (max_results={max_results})")

            # Run yt-dlp with flat-playlist to get metadata without downloading
            cmd = [
                "yt-dlp",
                f"ytsearch{max_results}:{query}",
                "--dump-json",
                "--flat-playlist",
                "--no-warnings"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp search failed: {result.stderr}")
                return []

            # Parse JSON output (one object per line)
            results = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    results.append({
                        "video_id": data["id"],
                        "title": html.unescape(data.get("title", "Unknown")),
                        "channel": html.unescape(data.get("uploader", "Unknown")),
                        "thumbnail_url": data.get("thumbnail", ""),
                        "description": html.unescape(data.get("description", "")),
                    })
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse yt-dlp result line: {e}")
                    continue

            logger.info(f"yt-dlp search returned {len(results)} results")
            return results

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp search timed out")
            return []
        except Exception as e:
            logger.error(f"yt-dlp search error: {type(e).__name__}: {e}")
            return []

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search for music videos on YouTube.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 10)

        Returns:
            List of search result dictionaries with keys:
                - video_id: YouTube video ID
                - title: Video title
                - channel: Channel name
                - thumbnail_url: URL to the video thumbnail
                - description: Video description
        """
        # Check cache first
        cached_results = self.cache.get(query)
        if cached_results is not None:
            logger.info(f"Cache hit for search: '{query}' ({len(cached_results)} results)")
            return cached_results[:max_results]

        # Mock mode: return fake data without calling API
        if self.mock_mode:
            logger.info(f"Mock search for: '{query}' (returning {min(max_results, len(MOCK_SEARCH_RESULTS))} results)")
            results = MOCK_SEARCH_RESULTS[:max_results]
            self.cache.set(query, results)
            return results

        # Try official API first (if available)
        try:
            logger.info(f"Searching YouTube API for: '{query}' (max_results={max_results})")

            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                videoCategoryId="10",  # Music category
                topicId="/m/04rlf",  # Music topic
                maxResults=max_results,
                safeSearch="moderate",
                videoEmbeddable="true",  # Filter for embeddable videos (reduces DRM)
                videoSyndicated="true"  # Filter for syndicated videos (reduces DRM)
            )
            response = request.execute()

            results = []
            skipped_count = 0

            for item in response.get("items", []):
                try:
                    # Skip if not a video or missing required fields
                    if "id" not in item or "videoId" not in item["id"]:
                        skipped_count += 1
                        logger.warning(f"Skipping result with missing videoId. Item id structure: {item.get('id', 'MISSING')}")
                        continue

                    snippet = item["snippet"]
                    results.append({
                        "video_id": item["id"]["videoId"],
                        "title": html.unescape(snippet["title"]),
                        "channel": html.unescape(snippet["channelTitle"]),
                        "thumbnail_url": snippet["thumbnails"]["high"]["url"],
                        "description": html.unescape(snippet["description"]),
                    })
                except (KeyError, TypeError) as e:
                    # Skip malformed results but log what went wrong
                    skipped_count += 1
                    logger.warning(f"Skipping malformed result - {type(e).__name__}: {e}. Item keys: {item.keys()}, id: {item.get('id', 'MISSING')}")
                    continue

            logger.info(f"API search returned {len(results)} valid results ({skipped_count} skipped)")

            # Cache the results
            self.cache.set(query, results)

            return results

        except Exception as e:
            # Official API failed - fall back to yt-dlp
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"YouTube API search failed ({error_type}: {error_msg}), falling back to yt-dlp")

            # Try yt-dlp fallback
            results = self.ytdlp_search(query, max_results)

            if results:
                # Cache the results
                self.cache.set(query, results)
                return results
            else:
                # Both methods failed
                logger.error(f"Both API and yt-dlp search failed for query: '{query}'")
                return []
