"""Audio URL caching to reduce playback latency."""
import os
import json
import time
from pathlib import Path
from typing import Optional


class AudioCache:
    """Cache audio URLs to speed up playback."""

    def __init__(self, cache_dir: str = ".cache"):
        """Initialize audio cache.

        Args:
            cache_dir: Directory to store cache data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "audio_urls.json"
        self.cache: dict = {}
        self.ttl = 3600 * 6  # 6 hours TTL for URLs
        self.load()

    def load(self) -> None:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def get(self, video_id: str) -> Optional[str]:
        """Get cached audio URL if available and not expired.

        Args:
            video_id: YouTube video ID

        Returns:
            Cached audio URL or None if not cached or expired
        """
        if video_id in self.cache:
            entry = self.cache[video_id]
            timestamp = entry.get("timestamp", 0)

            # Check if expired
            if time.time() - timestamp < self.ttl:
                return entry.get("url")

            # Remove expired entry
            del self.cache[video_id]
            self.save()

        return None

    def set(self, video_id: str, url: str) -> None:
        """Cache an audio URL.

        Args:
            video_id: YouTube video ID
            url: Direct audio stream URL
        """
        self.cache[video_id] = {
            "url": url,
            "timestamp": time.time()
        }
        self.save()

    def clear_expired(self) -> None:
        """Remove all expired entries from cache."""
        now = time.time()
        expired = [
            vid for vid, entry in self.cache.items()
            if now - entry.get("timestamp", 0) >= self.ttl
        ]

        for vid in expired:
            del self.cache[vid]

        if expired:
            self.save()
