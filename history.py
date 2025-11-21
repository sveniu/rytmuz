"""Track recently played songs."""
import json
import os
from datetime import datetime
from typing import List, Dict


class PlayHistory:
    """Manage play history for recent songs."""

    def __init__(self, history_file: str = ".history.json"):
        """Initialize play history.

        Args:
            history_file: Path to the history JSON file
        """
        self.history_file = history_file
        self.history: List[Dict] = []
        self.load()

    def load(self) -> None:
        """Load history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def save(self) -> None:
        """Save history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass

    def add(self, video_data: Dict) -> None:
        """Add a song to history.

        Args:
            video_data: Video metadata dictionary
        """
        entry = {
            "video_id": video_data["video_id"],
            "title": video_data["title"],
            "channel": video_data["channel"],
            "thumbnail_url": video_data["thumbnail_url"],
            "played_at": datetime.now().isoformat(),
        }

        # Remove if already exists (to update position)
        self.history = [h for h in self.history if h["video_id"] != video_data["video_id"]]

        # Add to beginning
        self.history.insert(0, entry)

        # Keep only last 50
        self.history = self.history[:50]

        self.save()

    def get_recent(self, count: int = 20) -> List[Dict]:
        """Get recent songs.

        Args:
            count: Number of recent songs to return

        Returns:
            List of recent song dictionaries
        """
        return self.history[:count]
