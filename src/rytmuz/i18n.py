"""Internationalization support for rytmuz."""
import os
import locale


# Language code aliases (e.g., nb/nn -> no)
LANGUAGE_ALIASES = {
    "nb": "no",  # Norwegian Bokmål -> Norwegian
    "nn": "no",  # Norwegian Nynorsk -> Norwegian
}


# Translation strings for each supported language
STRINGS = {
    "en": {
        # Input and placeholders
        "search_placeholder": "Search for music...",
        "loading": "Loading...",

        # Control buttons
        "seek_back": "⏮ -10s",
        "play_pause": "⏯ Play/Pause",
        "seek_forward": "⏭ +10s",
        "vol_down": "🔉 Vol-",
        "vol_up": "🔊 Vol+",
        "recent_button": "⏱ Recent",

        # Empty states
        "no_recent_songs": "No recent songs",
        "no_results": "No results found",

        # Status messages
        "loading_title": "Loading: {title}",
        "playing_title": "▶ Playing: {title}",
        "error": "Error: {error}",

        # Keyboard binding labels
        "focus_search": "Focus Search",
        "recent_songs": "Recent Songs",
        "back_to_player": "Back to Player",
        "debug": "Debug",
        "quit": "Quit",

        # Help screen
        "help_title": "RYTMUZ - Help",
        "help_keyboard_shortcuts": "Keyboard Shortcuts",
        "help_ctrl_s": "Ctrl+S    Focus search input",
        "help_ctrl_r": "Ctrl+R    Show recent songs",
        "help_space": "Space     Play/Pause",
        "help_escape": "Escape    Return to player",
        "help_f1": "F1        Show this help",
        "help_h": "h or ?    Show this help (when not typing)",
        "help_ctrl_c": "Ctrl+C    Quit",
        "help_player_controls": "Player Controls",
        "help_seek_back": "⏮  -10s     Seek backward 10 seconds",
        "help_play_pause": "⏯  Play/Pause   Toggle playback",
        "help_seek_forward": "⏭  +10s     Seek forward 10 seconds",
        "help_vol_down": "🔉 Vol-     Decrease volume",
        "help_vol_up": "🔊 Vol+     Increase volume",
        "help_usage_tips": "Usage Tips",
        "help_tip_search": "• Type in search box and press Enter to search",
        "help_tip_play": "• Click on a song card to play it",
        "help_tip_cache": "• Recent songs are cached for instant replay",
        "help_tip_escape": "• Press Escape to return to player view",
        "help_close": "Press Escape, F1, h, ?, or q to close this help",
    },
    "no": {  # Norwegian
        # Input and placeholders
        "search_placeholder": "Søk etter musikk...",
        "loading": "Laster...",

        # Control buttons
        "seek_back": "⏮ -10s",
        "play_pause": "⏯ Spill/Pause",
        "seek_forward": "⏭ +10s",
        "vol_down": "🔉 Vol-",
        "vol_up": "🔊 Vol+",
        "recent_button": "⏱ Nylige",

        # Empty states
        "no_recent_songs": "Ingen nylige sanger",
        "no_results": "Ingen resultater funnet",

        # Status messages
        "loading_title": "Laster: {title}",
        "playing_title": "▶ Spiller: {title}",
        "error": "Feil: {error}",

        # Keyboard binding labels
        "focus_search": "Fokuser søk",
        "recent_songs": "Nylige sanger",
        "back_to_player": "Tilbake til spiller",
        "debug": "Feilsøking",
        "quit": "Avslutt",

        # Help screen
        "help_title": "RYTMUZ - Hjelp",
        "help_keyboard_shortcuts": "Tastatursnarveier",
        "help_ctrl_s": "Ctrl+S    Fokuser søkefelt",
        "help_ctrl_r": "Ctrl+R    Vis nylige sanger",
        "help_space": "Space     Spill/Pause",
        "help_escape": "Escape    Tilbake til spiller",
        "help_f1": "F1        Vis denne hjelpen",
        "help_h": "h eller ? Vis denne hjelpen (når du ikke skriver)",
        "help_ctrl_c": "Ctrl+C    Avslutt",
        "help_player_controls": "Avspillingskontroller",
        "help_seek_back": "⏮  -10s     Spol tilbake 10 sekunder",
        "help_play_pause": "⏯  Spill/Pause   Bytt avspilling",
        "help_seek_forward": "⏭  +10s     Spol frem 10 sekunder",
        "help_vol_down": "🔉 Vol-     Senk volumet",
        "help_vol_up": "🔊 Vol+     Øk volumet",
        "help_usage_tips": "Brukertips",
        "help_tip_search": "• Skriv i søkeboksen og trykk Enter for å søke",
        "help_tip_play": "• Klikk på et sangkort for å spille det",
        "help_tip_cache": "• Nylige sanger blir hurtigbufret for umiddelbar avspilling",
        "help_tip_escape": "• Trykk Escape for å gå tilbake til spillervisning",
        "help_close": "Trykk Escape, F1, h, ? eller q for å lukke denne hjelpen",
    },
}


def get_locale() -> str:
    """Get the current system locale language code.

    Returns:
        Two-letter language code (e.g., 'en', 'no', 'de')
    """
    # Check RYTMUZ_LANG environment variable first
    env_lang = os.environ.get("RYTMUZ_LANG")
    if env_lang:
        return env_lang.lower()[:2]

    # Try to get system locale
    try:
        # Get locale from environment or system
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            # Extract language code (e.g., 'en_US' -> 'en')
            return system_locale.split('_')[0].lower()
    except Exception:
        pass

    # Default to English
    return "en"


# Global current language
_current_lang = get_locale()


def set_language(lang_code: str) -> None:
    """Set the current language.

    Args:
        lang_code: Two-letter language code (e.g., 'en', 'no', 'nb', 'nn')
    """
    global _current_lang
    # Apply alias mapping and check if valid
    resolved_lang = LANGUAGE_ALIASES.get(lang_code, lang_code)
    if resolved_lang in STRINGS:
        _current_lang = lang_code  # Store original, resolve at get_text time
    else:
        _current_lang = "en"


def get_text(key: str, **kwargs) -> str:
    """Get translated text for a key.

    Args:
        key: Translation key
        **kwargs: Format string parameters

    Returns:
        Translated and formatted string, or key if translation missing
    """
    # Apply language alias mapping
    resolved_lang = LANGUAGE_ALIASES.get(_current_lang, _current_lang)

    # Get translations for current language, fall back to English
    translations = STRINGS.get(resolved_lang, STRINGS["en"])
    text = translations.get(key)

    # Fall back to English if key not found in current language
    if text is None:
        text = STRINGS["en"].get(key, key)

    # Apply format parameters if any
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text

    return text


# Convenience alias (common i18n pattern)
_ = get_text
