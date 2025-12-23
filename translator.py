from google import genai
import config


class TranslationService:
    """Translate text using Gemini AI for high-quality contextual translations."""
    
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
    
    # Custom prompt for voiceover-ready translations
    TRANSLATION_PROMPT = """You are a professional translator specializing in sports content localization for voiceover.

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

Translate the following text to {target_language}:

{text}

Provide ONLY the translated text, nothing else."""

    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    def translate(self, text, target_lang='en'):
        """
        Translate text to target language using Gemini.
        Returns: dict with translated_text, success status
        """
        try:
            target_language = self.LANGUAGES.get(target_lang, target_lang)
            
            prompt = self.TRANSLATION_PROMPT.format(
                target_language=target_language,
                text=text
            )
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt
            )
            translated_text = response.text.strip()
            
            return {
                'success': True,
                'translated_text': translated_text,
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
