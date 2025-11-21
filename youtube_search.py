"""YouTube search functionality using Google API."""
import os
import html
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from mock_data import MOCK_SEARCH_RESULTS

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

        if not mock_mode:
            self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
            if not self.api_key:
                raise ValueError("YouTube API key not provided and YOUTUBE_API_KEY env var not set")

            self.youtube = build("youtube", "v3", developerKey=self.api_key)
        else:
            logger.info("Mock mode enabled - using fake search results")
            self.api_key = None
            self.youtube = None

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
        # Mock mode: return fake data without calling API
        if self.mock_mode:
            logger.info(f"Mock search for: '{query}' (returning {min(max_results, len(MOCK_SEARCH_RESULTS))} results)")
            return MOCK_SEARCH_RESULTS[:max_results]

        try:
            logger.info(f"Searching YouTube for: '{query}' (max_results={max_results})")

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

            logger.info(f"Search returned {len(results)} valid results ({skipped_count} skipped)")
            return results

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise Exception(f"YouTube API error: {e}")
