"""Multi-Language Support for Eden Analytics Pro."""

import json
from pathlib import Path
from typing import Dict, Optional
import locale

from utils.logger import get_logger

logger = get_logger(__name__)


class Translator:
    """Manages translations for the application."""
    
    SUPPORTED_LANGUAGES = ['en', 'ru']
    DEFAULT_LANGUAGE = 'en'
    
    def __init__(self, language: str = None):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = language or self._detect_language()
        
        self._load_translations()
    
    def _detect_language(self) -> str:
        """Detect system language."""
        try:
            system_lang = locale.getdefaultlocale()[0]
            if system_lang:
                lang_code = system_lang.split('_')[0].lower()
                if lang_code in self.SUPPORTED_LANGUAGES:
                    return lang_code
        except Exception:
            pass
        return self.DEFAULT_LANGUAGE
    
    def _load_translations(self):
        """Load all translation files."""
        translations_dir = Path(__file__).parent
        
        for lang in self.SUPPORTED_LANGUAGES:
            file_path = translations_dir / f"{lang}.json"
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang] = json.load(f)
                    logger.debug(f"Loaded translations for {lang}")
                else:
                    self.translations[lang] = {}
                    logger.warning(f"Translation file not found: {file_path}")
            except Exception as e:
                logger.error(f"Error loading {lang} translations: {e}")
                self.translations[lang] = {}
    
    def set_language(self, language: str):
        """Set current language."""
        if language in self.SUPPORTED_LANGUAGES:
            self.current_language = language
            logger.info(f"Language set to: {language}")
        else:
            logger.warning(f"Unsupported language: {language}")
    
    def get_language(self) -> str:
        """Get current language."""
        return self.current_language
    
    def t(self, key: str, **kwargs) -> str:
        """Translate a key.
        
        Args:
            key: Translation key (e.g., 'menu.file')
            **kwargs: Variables for string formatting
        
        Returns:
            Translated string or key if not found
        """
        # Get translation from current language
        translation = self._get_nested_value(
            self.translations.get(self.current_language, {}),
            key
        )
        
        # Fallback to English
        if translation is None and self.current_language != 'en':
            translation = self._get_nested_value(
                self.translations.get('en', {}),
                key
            )
        
        # Return key if not found
        if translation is None:
            return key
        
        # Apply formatting
        if kwargs:
            try:
                return translation.format(**kwargs)
            except KeyError:
                return translation
        
        return translation
    
    def _get_nested_value(self, d: Dict, key: str) -> Optional[str]:
        """Get nested dictionary value using dot notation."""
        keys = key.split('.')
        value = d
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def get_all_keys(self) -> Dict[str, str]:
        """Get all translation keys for current language."""
        return self.translations.get(self.current_language, {})


# Global translator instance
_translator: Optional[Translator] = None


def get_translator() -> Translator:
    """Get the global translator instance."""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator


def set_language(language: str):
    """Set the global language."""
    get_translator().set_language(language)


def t(key: str, **kwargs) -> str:
    """Shortcut for translation."""
    return get_translator().t(key, **kwargs)


__all__ = ['Translator', 'get_translator', 'set_language', 't']
