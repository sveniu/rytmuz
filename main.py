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
        align: center middle;
    }

    #player-content {
        width: auto;
        align: center middle;
    }

    #player-thumbnail {
        width: auto;
        height: auto;
        margin-bottom: 2;
        align: center middle;
    }

    #now-playing {
        text-align: center;
        margin: 1;
        width: 100%;
    }

    #controls-container {
        align: center middle;
        width: auto;
    }

    .control-button {
        margin: 0 1;
    }

    .hidden {
        display: none;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "focus_search", "Focus Search", show=True),
        Binding("ctrl+r", "show_recent", "Recent Songs", show=True),
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
            with Container(id="player-view", classes="hidden"):
                with Vertical(id="player-content"):
                    yield Static("", id="player-thumbnail")
                    yield Label("Loading...", id="now-playing")
                    with Horizontal(id="controls-container"):
                        yield Button("⏮ -10s", id="seek-back", classes="control-button")
                        yield Button("⏯ Play/Pause", id="play-pause", classes="control-button")
                        yield Button("⏭ +10s", id="seek-forward", classes="control-button")
                        yield Button("🔉 Vol-", id="vol-down", classes="control-button")
                        yield Button("🔊 Vol+", id="vol-up", classes="control-button")

    def action_focus_search(self) -> None:
        """Focus the search input and show results view."""
        # Show results view, hide player view
        self.query_one("#results-split").remove_class("hidden")
        self.query_one("#player-view").add_class("hidden")
        self.query_one("#search-input", Input).focus()

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
        self.query_one("#search-input", Input).focus()

        # Initialize YouTube searcher
        api_key_file = "api_key"
        if os.path.exists(api_key_file):
            with open(api_key_file) as f:
                api_key = f.read().strip()
            self.searcher = YouTubeSearcher(api_key)
        else:
            self.searcher = YouTubeSearcher()

        # Initialize audio player
        self.player = AudioPlayer()

        # Initialize play history
        self.history = PlayHistory()

    def on_unmount(self) -> None:
        """Called when app exits - cleanup."""
        # Stop any playing audio
        if hasattr(self, 'player'):
            self.player.stop()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search when user presses Enter."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
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
            # Use 80% of pane width to leave padding, with sensible bounds
            max_width = max(20, min(35, int(pane_width * 0.8))) if pane_width > 0 else 30
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
            self.play_video(video_data)

    @work(thread=True)
    def play_video(self, video_data: dict) -> None:
        """Start playing a video."""
        video_id = video_data["video_id"]
        title = video_data["title"]
        thumbnail_url = video_data["thumbnail_url"]

        def update_status(msg):
            now_playing = self.query_one("#now-playing", Label)
            now_playing.update(msg)

        self.call_from_thread(update_status, f"Loading: {title}")

        try:
            # Download and display larger thumbnail
            thumbnail = download_thumbnail(thumbnail_url, max_width=50)

            def update_thumbnail():
                thumbnail_display = self.query_one("#player-thumbnail", Static)
                thumbnail_display.update(thumbnail)

            self.call_from_thread(update_thumbnail)

            self.player.play(video_id)
            self.call_from_thread(update_status, f"▶ Playing: {title}")

            # Add to history
            self.history.add(video_data)
        except Exception as e:
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
