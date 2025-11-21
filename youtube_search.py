"""YouTube search functionality using Google API."""
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeSearcher:
    """Handle YouTube searches using the official API."""

    def __init__(self, api_key: str | None = None):
        """Initialize the YouTube searcher.

        Args:
            api_key: YouTube Data API v3 key. If None, reads from YOUTUBE_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key not provided and YOUTUBE_API_KEY env var not set")

        self.youtube = build("youtube", "v3", developerKey=self.api_key)

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
        try:
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
            for item in response.get("items", []):
                snippet = item["snippet"]
                results.append({
                    "video_id": item["id"]["videoId"],
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "thumbnail_url": snippet["thumbnails"]["high"]["url"],
                    "description": snippet["description"],
                })

            return results

        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
