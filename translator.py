from google import genai
from deep_translator import GoogleTranslator
import config


class TranslationService:
    """
    Hybrid translation service:
    - Gemini AI for Original → English (high-quality, contextual, removes intro/outro)
    - Google Translate for English → Other languages (free, unlimited)
    """
    
    LANGUAGES = {
        'en': 'English',
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
    
    # Custom prompt for voiceover-ready translations (English only)
    ENGLISH_PROMPT = """You are a professional translator specializing in sports content localization for voiceover.

RULES:
1. NO intro phrases (like "Welcome to...", "Hello everyone...")
2. NO outro phrases (like "See you next time...", "Subscribe...")
3. NO mentions of "Raf Talks" or channel names
4. NO "—" symbols
5. NO extra commentary or explanations
6. Keep the natural flow suitable for voiceover narration
7. Maintain the original meaning and context
8. Use proper sentence structure, not word-by-word translation
9. Keep sports terminology accurate (Ballon d'Or, not "ballad" or "golden ball")

Translate the following text to English:

{text}

Provide ONLY the translated text, nothing else."""

    def __init__(self):
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    def translate(self, text, target_lang='en'):
        """
        Translate text to target language.
        - English: Uses Gemini API (high-quality, contextual)
        - Other languages: Uses Google Translate (free, no API limits)
        """
        try:
            if target_lang == 'en':
                # Use Gemini for English (needs context and quality)
                return self._translate_with_gemini(text)
            else:
                # Use Google Translate for other languages (from English)
                return self._translate_with_google(text, target_lang)
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _translate_with_gemini(self, text):
        """Translate to English using Gemini API with custom rules."""
        prompt = self.ENGLISH_PROMPT.format(text=text)
        
        response = self.gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        translated_text = response.text.strip()
        
        return {
            'success': True,
            'translated_text': translated_text,
            'target_lang': 'en',
            'method': 'gemini'
        }
    
    def _translate_with_google(self, text, target_lang):
        """Translate from English to other languages using Google Translate."""
        translator = GoogleTranslator(source='en', target=target_lang)
        translated_text = translator.translate(text)
        
        return {
            'success': True,
            'translated_text': translated_text,
            'target_lang': target_lang,
            'method': 'google'
        }
    
    @classmethod
    def get_languages(cls):
        """Return available language options."""
        return cls.LANGUAGES
