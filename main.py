import os
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, Button, Static, Label, ListItem, ListView
from textual.binding import Binding
from textual.message import Message
from textual import work

from youtube_search import YouTubeSearcher
from thumbnail import download_thumbnail
from player import AudioPlayer
from history import PlayHistory


class SearchResultItem(ListItem):
    """A custom list item for search results."""

    def __init__(self, video_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_data = video_data


class RytmuzApp(App):
    """A kid-friendly YouTube music player."""

    # Debug mode - toggle with Ctrl+D
    debug_mode = False

    CSS = """
    Screen {
        align: center top;
    }

    #search-container {
        dock: top;
        height: 5;
        padding: 1;
        background: $panel;
    }

    #search-input {
        width: 100%;
    }

    #main-content {
        height: 1fr;
    }

    #results-split {
        height: 100%;
    }

    #results-list-container {
        width: 60%;
        height: 100%;
        border-right: solid $primary;
    }

    #results-list {
        height: 100%;
    }

    #preview-pane {
        width: 40%;
        height: 100%;
        padding: 1;
        align: center middle;
    }

    SearchResultItem {
        height: 1;
        padding: 0 1;
    }

    SearchResultItem:hover {
        background: $boost;
    }

    #player-view {
        height: 100%;
        layout: vertical;
    }

    #player-content {
        width: 100%;
        height: 1fr;
        overflow: hidden;
        align: center middle;
        content-align: center middle;
    }

    #player-thumbnail {
        width: 100%;
        height: auto;
        margin: 0;
        padding: 0;
        align: center middle;
        content-align: center middle;
    }

    #now-playing {
        text-align: center;
        margin: 0 0 1 0;
        padding: 0;
        width: 100%;
        height: auto;
    }

    #controls-container {
        align: center middle;
        width: 100%;
        height: 3;
        content-align: center middle;
        margin: 0;
        padding: 0;
    }

    .control-button {
        margin: 0 1;
    }

    .hidden {
        display: none;
    }

    #debug-info {
        dock: bottom;
        height: 1;
        background: $panel;
        text-align: center;
        color: $text-muted;
        display: none;
    }

    #debug-info.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "focus_search", "Focus Search", show=True),
        Binding("ctrl+r", "show_recent", "Recent Songs", show=True),
        Binding("escape", "back_to_player", "Back to Player", show=True),
        Binding("ctrl+d", "toggle_debug", "Debug", show=False),
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="search-container"):
            yield Input(placeholder="Search for music...", id="search-input")

        with Container(id="main-content"):
            # Results split view (left: list, right: preview)
            with Horizontal(id="results-split"):
                with Vertical(id="results-list-container"):
                    yield ListView(id="results-list")
                yield Static("", id="preview-pane")

            # Player view (shown during playback)
            with Vertical(id="player-view", classes="hidden"):
                with Container(id="player-content"):
                    yield Static("", id="player-thumbnail")
                yield Label("Loading...", id="now-playing")
                with Horizontal(id="controls-container"):
                    yield Button("⏮ -10s", id="seek-back", classes="control-button")
                    yield Button("⏯ Play/Pause", id="play-pause", classes="control-button")
                    yield Button("⏭ +10s", id="seek-forward", classes="control-button")
                    yield Button("🔉 Vol-", id="vol-down", classes="control-button")
                    yield Button("🔊 Vol+", id="vol-up", classes="control-button")

        # Debug info at bottom
        yield Label("", id="debug-info")

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        debug_label = self.query_one("#debug-info", Label)
        if self.debug_mode:
            debug_label.add_class("visible")
        else:
            debug_label.remove_class("visible")

    def action_focus_search(self) -> None:
        """Focus the search input and show results view."""
        # Show results view, hide player view
        self.query_one("#results-split").remove_class("hidden")
        self.query_one("#player-view").add_class("hidden")
        self.query_one("#search-input", Input).focus()

    def action_back_to_player(self) -> None:
        """Return to player view if music is playing."""
        # Only switch if player view has content (something is playing)
        if self.player.is_playing:
            self.query_one("#results-split").add_class("hidden")
            self.query_one("#player-view").remove_class("hidden")

    def action_show_recent(self) -> None:
        """Show recent songs."""
        # Show results view, hide player view
        self.query_one("#results-split").remove_class("hidden")
        self.query_one("#player-view").add_class("hidden")

        results_list = self.query_one("#results-list", ListView)
        results_list.clear()

        recent_songs = self.history.get_recent(20)

        if not recent_songs:
            results_list.append(ListItem(Label("No recent songs")))
            return

        for song in recent_songs:
            title = song["title"]
            channel = song["channel"]
            item_label = Label(f"{title} [dim]· {channel}[/dim]")
            item = SearchResultItem(song, item_label)
            results_list.append(item)

    def on_mount(self) -> None:
        """Called when app starts."""
        self.log("=" * 80)
        self.log("RYTMUZ starting up")
        self.log(f"Textual version: {self.app.TEXTUAL_VERSION if hasattr(self.app, 'TEXTUAL_VERSION') else 'unknown'}")
        self.query_one("#search-input", Input).focus()

        # Initialize YouTube searcher
        api_key_file = "api_key"
        if os.path.exists(api_key_file):
            with open(api_key_file) as f:
                api_key = f.read().strip()
            self.searcher = YouTubeSearcher(api_key)
            self.log("YouTube searcher initialized with API key from file")
        else:
            self.searcher = YouTubeSearcher()
            self.log("YouTube searcher initialized with API key from env")

        # Initialize audio player
        self.player = AudioPlayer()
        self.log("Audio player initialized")

        # Initialize play history
        self.history = PlayHistory()
        self.log(f"Play history loaded: {len(self.history.get_recent(50))} songs")

    def on_unmount(self) -> None:
        """Called when app exits - cleanup."""
        self.log("RYTMUZ shutting down")
        # Stop any playing audio
        if hasattr(self, 'player'):
            self.player.stop()
            self.log("Audio player stopped")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search when user presses Enter."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self.log(f"User submitted search query: '{query}'")
                # Ensure results view is visible
                self.query_one("#results-split").remove_class("hidden")
                self.query_one("#player-view").add_class("hidden")
                # Clear old results immediately
                results_list = self.query_one("#results-list", ListView)
                results_list.clear()
                # Clear preview pane
                self.query_one("#preview-pane", Static).update("")
                self.perform_search(query)

    @work(thread=True)
    def perform_search(self, query: str) -> None:
        """Perform a YouTube search and display results."""
        try:
            results = self.searcher.search(query, max_results=15)

            # Clear results list from main thread
            def clear_results():
                results_list = self.query_one("#results-list", ListView)
                results_list.clear()

            self.call_from_thread(clear_results)

            if not results:
                def add_no_results():
                    results_list = self.query_one("#results-list", ListView)
                    results_list.append(ListItem(Label("No results found")))
                self.call_from_thread(add_no_results)
                return

            for result in results:
                title = result["title"]
                channel = result["channel"]

                def add_result(r=result):
                    results_list = self.query_one("#results-list", ListView)
                    item_label = Label(f"{r['title']} [dim]· {r['channel']}[/dim]")
                    item = SearchResultItem(r, item_label)
                    results_list.append(item)

                self.call_from_thread(add_result)

        except Exception as e:
            def add_error():
                results_list = self.query_one("#results-list", ListView)
                results_list.append(ListItem(Label(f"[red]Error: {e}[/red]")))
            self.call_from_thread(add_error)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Show thumbnail preview when hovering over a result."""
        if isinstance(event.item, SearchResultItem):
            # Get preview pane dimensions from main thread
            preview_pane = self.query_one("#preview-pane", Static)
            pane_width = preview_pane.size.width

            # Get terminal width for comparison
            terminal_width = self.size.width

            # Use almost full pane width, leaving just 2 chars for minimal padding
            if pane_width > 0:
                max_width = max(15, pane_width - 2)
            else:
                max_width = 30  # Fallback

            # Display debug info if enabled
            if self.debug_mode:
                debug_label = self.query_one("#debug-info", Label)
                debug_label.update(
                    f"Terminal: {terminal_width}ch | Preview pane: {pane_width}ch | "
                    f"Thumbnail: {max_width}ch | Pane%: {pane_width/terminal_width*100:.1f}%"
                )

            self.show_preview_thumbnail(event.item.video_data, max_width)

    @work(thread=True)
    def show_preview_thumbnail(self, video_data: dict, max_width: int) -> None:
        """Load and display thumbnail in preview pane."""
        thumbnail_url = video_data["thumbnail_url"]
        thumbnail = download_thumbnail(thumbnail_url, max_width=max_width)

        def update_preview():
            preview_pane = self.query_one("#preview-pane", Static)
            preview_pane.update(thumbnail)

        self.call_from_thread(update_preview)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle when a search result is selected."""
        if isinstance(event.item, SearchResultItem):
            video_data = event.item.video_data
            # Hide results, show player view
            self.query_one("#results-split").add_class("hidden")
            self.query_one("#player-view").remove_class("hidden")

            # Simple approach: size based on width, let layout constrain height
            terminal_width = self.size.width
            # Use 60% of terminal width
            thumb_width = int(terminal_width * 0.6)

            self.play_video(video_data, thumb_width)

    @work(thread=True)
    def play_video(self, video_data: dict, thumb_width: int) -> None:
        """Start playing a video."""
        video_id = video_data["video_id"]
        title = video_data["title"]
        thumbnail_url = video_data["thumbnail_url"]

        def update_status(msg):
            now_playing = self.query_one("#now-playing", Label)
            now_playing.update(msg)

        def log_msg(msg):
            self.call_from_thread(self.log, msg)

        log_msg(f"Starting playback: '{title}' (video_id={video_id})")
        self.call_from_thread(update_status, f"Loading: {title}")

        try:
            # Download and display thumbnail at calculated size
            log_msg(f"Downloading thumbnail (width={thumb_width})")
            thumbnail = download_thumbnail(thumbnail_url, max_width=thumb_width)

            def update_thumbnail():
                thumbnail_display = self.query_one("#player-thumbnail", Static)
                thumbnail_display.update(thumbnail)

            self.call_from_thread(update_thumbnail)
            log_msg("Thumbnail displayed")

            log_msg("Starting mpv playback")
            self.player.play(video_id)
            self.call_from_thread(update_status, f"▶ Playing: {title}")
            log_msg("Playback started successfully")

            # Add to history
            self.history.add(video_data)
            log_msg("Added to play history")
        except Exception as e:
            log_msg(f"Playback error: {type(e).__name__}: {e}")
            self.call_from_thread(update_status, f"Error: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id

        if button_id == "play-pause":
            self.player.toggle_pause()
        elif button_id == "seek-back":
            self.player.seek(-10)
        elif button_id == "seek-forward":
            self.player.seek(10)
        elif button_id == "vol-down":
            self.player.adjust_volume(-5)
        elif button_id == "vol-up":
            self.player.adjust_volume(5)


def main():
    app = RytmuzApp()
    app.run()


if __name__ == "__main__":
    main()
