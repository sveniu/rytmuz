"""Internationalization support for rytmuz."""
import os
import locale


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
        lang_code: Two-letter language code (e.g., 'en', 'no')
    """
    global _current_lang
    if lang_code in STRINGS:
        _current_lang = lang_code
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
    # Get translations for current language, fall back to English
    translations = STRINGS.get(_current_lang, STRINGS["en"])
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
