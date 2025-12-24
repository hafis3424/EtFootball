from google import genai
from deep_translator import GoogleTranslator
import config


# Global current model state
_current_model = config.DEFAULT_MODEL


class TranslationService:
    """
    Hybrid translation service:
    - Gemini/Gemma AI for Original → English (high-quality, contextual, removes intro/outro)
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
    
    # Custom prompt for voiceover-ready translations (works for both Gemini and Gemma)
    ENGLISH_PROMPT = """You are a professional translator specializing in sports content localization for voiceover.

CRITICAL OUTPUT FORMAT RULES:
1. Output as CONTINUOUS FLOWING PARAGRAPHS - NO line breaks within sentences
2. Use natural paragraph breaks ONLY for major topic changes (maximum 2-3 paragraphs for short content)
3. Write as smooth, flowing prose suitable for voiceover narration

CONTENT RULES:
1. NO intro phrases (like "Welcome to...", "Hello everyone...", "Namaskar...")
2. NO outro phrases (like "See you next time...", "Subscribe...", "will be back with...")
3. NO mentions of "Raf Talks" or any channel names
4. NO "—" symbols
5. NO extra commentary or explanations
6. Maintain the original meaning and context
7. Use proper sentence structure, not word-by-word translation
8. Keep sports terminology accurate (Ballon d'Or, not "ballad" or "golden ball")

Translate the following text to English:

{text}

Provide ONLY the translated text as flowing paragraphs, nothing else."""

    def __init__(self):
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    @staticmethod
    def get_current_model():
        """Get the currently selected model."""
        global _current_model
        return _current_model
    
    @staticmethod
    def set_current_model(model_name):
        """Set the current model to use."""
        global _current_model
        if model_name in config.AVAILABLE_MODELS:
            _current_model = model_name
            return True
        return False
    
    @staticmethod
    def get_available_models():
        """Return available models with their info."""
        return config.AVAILABLE_MODELS
    
    def translate(self, text, target_lang='en'):
        """
        Translate text to target language.
        - English: Uses Gemini/Gemma API (high-quality, contextual)
        - Other languages: Uses Google Translate (free, no API limits)
        """
        try:
            if target_lang == 'en':
                # Use Gemini/Gemma for English (needs context and quality)
                return self._translate_with_ai(text)
            else:
                # Use Google Translate for other languages (from English)
                return self._translate_with_google(text, target_lang)
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _translate_with_ai(self, text):
        """Translate to English using current AI model with custom rules."""
        global _current_model
        prompt = self.ENGLISH_PROMPT.format(text=text)
        
        response = self.gemini_client.models.generate_content(
            model=_current_model,
            contents=prompt
        )
        translated_text = response.text.strip()
        
        # Clean up excessive line breaks (normalize to max 2 consecutive newlines)
        import re
        translated_text = re.sub(r'\n{3,}', '\n\n', translated_text)
        # Replace single newlines with spaces (keep only paragraph breaks)
        translated_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', translated_text)
        
        return {
            'success': True,
            'translated_text': translated_text,
            'target_lang': 'en',
            'method': 'ai',
            'model': _current_model
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
