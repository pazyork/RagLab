import json
import os
from pathlib import Path
from typing import Dict, Optional

# Module-level language state
_current_lang: str = "zh"

# Cache for loaded translations
_translations: Dict[str, Dict[str, str]] = {}

# Get the directory of this file
_i18n_dir = Path(__file__).parent


def _load_translations(lang: str) -> Dict[str, str]:
    """Load translations from JSON file for the given language."""
    if lang in _translations:
        return _translations[lang]

    file_path = _i18n_dir / f"{lang}.json"

    if not file_path.exists():
        _translations[lang] = {}
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
        _translations[lang] = translations
        return translations
    except (json.JSONDecodeError, IOError):
        _translations[lang] = {}
        return {}


def t(key: str) -> str:
    """Return the translation for the given key in the current language.

    If the key is not found, returns the key itself.
    """
    translations = _load_translations(_current_lang)
    return translations.get(key, key)


def set_lang(lang: str) -> None:
    """Set the current language."""
    global _current_lang
    _current_lang = lang


def get_lang() -> str:
    """Get the current language."""
    return _current_lang
