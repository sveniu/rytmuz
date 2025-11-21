"""Audio playback using yt-dlp and mpv."""
import subprocess
import threading
from typing import Optional, Callable

from cache import AudioCache


class AudioPlayer:
    """Manage audio playback using yt-dlp and mpv."""

    def __init__(self):
        """Initialize the audio player."""
        self.mpv_process: Optional[subprocess.Popen] = None
        self.current_video_id: Optional[str] = None
        self.is_playing: bool = False
        self._ipc_socket = "/tmp/rytmuz_mpv_socket"
        self.cache = AudioCache()

    def get_audio_url(self, video_id: str) -> str:
        """Get the direct audio URL using yt-dlp with caching.

        Args:
            video_id: YouTube video ID

        Returns:
            Direct audio stream URL
        """
        # Check cache first
        cached_url = self.cache.get(video_id)
        if cached_url:
            return cached_url

        # Fetch from yt-dlp
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            result = subprocess.run(
                ["yt-dlp", "-g", "-f", "bestaudio", youtube_url],
                capture_output=True,
                text=True,
                check=True,
                timeout=15
            )
            url = result.stdout.strip()

            # Cache the URL
            self.cache.set(video_id, url)

            return url
        except subprocess.CalledProcessError as e:
            raise Exception(f"yt-dlp failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("yt-dlp timed out")

    def play(self, video_id: str, on_end: Optional[Callable] = None) -> None:
        """Start playing audio.

        Args:
            video_id: YouTube video ID to play
            on_end: Optional callback when playback ends
        """
        # Stop current playback if any
        self.stop()

        try:
            # Get audio URL
            audio_url = self.get_audio_url(video_id)

            # Start mpv with IPC for control
            self.mpv_process = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--audio-display=no",
                    f"--input-ipc-server={self._ipc_socket}",
                    audio_url
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.current_video_id = video_id
            self.is_playing = True

            # Monitor playback in background
            if on_end:
                def monitor():
                    if self.mpv_process:
                        self.mpv_process.wait()
                        self.is_playing = False
                        on_end()

                threading.Thread(target=monitor, daemon=True).start()

        except Exception as e:
            raise Exception(f"Failed to start playback: {e}")

    def stop(self) -> None:
        """Stop current playback."""
        if self.mpv_process:
            self.mpv_process.terminate()
            try:
                self.mpv_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
            self.mpv_process = None

        self.is_playing = False
        self.current_video_id = None

    def toggle_pause(self) -> None:
        """Toggle pause/play state."""
        if self.mpv_process:
            self._send_command("cycle pause")

    def seek(self, seconds: int) -> None:
        """Seek forward or backward.

        Args:
            seconds: Number of seconds to seek (positive or negative)
        """
        if self.mpv_process:
            self._send_command(f"seek {seconds}")

    def adjust_volume(self, amount: int) -> None:
        """Adjust volume.

        Args:
            amount: Amount to adjust (positive or negative)
        """
        if self.mpv_process:
            self._send_command(f"add volume {amount}")

    def _send_command(self, command: str) -> None:
        """Send command to mpv via IPC.

        Args:
            command: MPV command to send
        """
        try:
            subprocess.run(
                ["socat", "-", self._ipc_socket],
                input=f'{{ "command": [{", ".join(f\'"{c}\' for c in command.split())}] }}\n',
                capture_output=True,
                text=True,
                timeout=1
            )
        except Exception:
            pass  # Silently ignore IPC failures
