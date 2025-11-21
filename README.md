# RYTMUZ

A kid-friendly YouTube music player built with Python, Textualize, yt-dlp, and mpv.

## Features

- **Music-only focus**: Audio playback only, no video distractions
- **Easy search**: Always-available search field with Ctrl+S hotkey
- **Recent songs**: Quick access to recently played songs with Ctrl+R
- **Simple controls**: Play/pause, seek ±10s, volume adjustment
- **Smart caching**: Fast replay of recent songs (sub-second vs 10+ seconds)
- **Visual feedback**: Thumbnails displayed using ASCII art
- **Kid-friendly**: Safe search enabled, focused on music discovery

## Requirements

- Python 3.13+
- `yt-dlp` command-line tool
- `mpv` media player
- YouTube Data API v3 key

## Setup

1. Install system dependencies:
   ```bash
   # Ubuntu/Debian
   sudo apt install yt-dlp mpv

   # macOS
   brew install yt-dlp mpv
   ```

2. Set up YouTube API key:
   - Get an API key from Google Cloud Console
   - Either:
     - Create an `api_key` file in the project directory, or
     - Set the `YOUTUBE_API_KEY` environment variable

3. Run the app:
   ```bash
   uv run main.py
   ```

## Usage

- **Search**: Type in the search box and press Enter, or press Ctrl+S to focus search
- **Play song**: Click on a search result or press Enter when focused
- **Recent songs**: Press Ctrl+R to view recently played songs
- **Controls**:
  - Play/Pause: Click the ⏯ button
  - Seek backward: ⏮ (-10s)
  - Seek forward: ⏭ (+10s)
  - Volume: 🔉/🔊 buttons
- **Quit**: Press Ctrl+C

## Architecture

- `main.py`: Textual TUI application
- `youtube_search.py`: YouTube Data API integration
- `player.py`: Audio playback with yt-dlp + mpv
- `cache.py`: URL caching for fast replay
- `history.py`: Play history tracking
- `thumbnail.py`: Image display with rich-pixels

## Design Decisions

- **No queueing**: Immediate playback on selection (may add later)
- **No auto-next**: Stops after song ends (may add YouTube recommendations later)
- **Audio-only**: No visualization to encourage listening and dancing vs screen time
- **Fast replay**: Cached URLs enable instant playback for favorite songs
