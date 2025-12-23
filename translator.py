from deep_translator import GoogleTranslator


class TranslationService:
    """Translate text using Google Translate via deep-translator."""
    
    LANGUAGES = {
        'es': 'Spanish',
        'pt': 'Portuguese',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'zh-CN': 'Chinese (Simplified)',
        'ja': 'Japanese',
        'ko': 'Korean'
    }
    
    def translate(self, text, target_lang='es'):
        """
        Translate text to target language.
        Returns: dict with translated_text, source_lang, target_lang
        """
        try:
            # deep-translator handles auto-detection of source language
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return {
                'success': True,
                'translated_text': translated,
                'target_lang': target_lang
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def get_languages(cls):
        """Return available language options."""
        return cls.LANGUAGES
