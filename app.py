from flask import Flask, render_template, jsonify, request
from youtube_api import YouTubeChannel
from transcriber import TranscriptExtractor
from translator import TranslationService
import config
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

yt = YouTubeChannel(config.YOUTUBE_API_KEY)
transcriber = TranscriptExtractor()
translator = TranslationService()

# Resolve channel ID once at startup
CHANNEL_ID = yt.resolve_handle(config.RAF_TALKS_HANDLE)
if CHANNEL_ID:
    config.RAF_TALKS_CHANNEL_ID = CHANNEL_ID
    print(f"Resolved @RafTalks to channel ID: {CHANNEL_ID}")
else:
    print("Warning: Could not resolve channel ID for @RafTalks")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/translate')
def translate_page():
    return render_template('translate.html')


@app.route('/api/channel/videos', methods=['GET'])
def get_videos():
    page_token = request.args.get('pageToken')
    if not config.RAF_TALKS_CHANNEL_ID:
        return jsonify({'error': 'Channel ID not set'}), 400
    
    # In dev mode, limit to 5 videos
    max_results = config.DEV_VIDEO_LIMIT if config.DEV_MODE else 50
    
    videos, next_page = yt.get_channel_videos(
        config.RAF_TALKS_CHANNEL_ID, 
        max_results=max_results,
        page_token=page_token
    )
    return jsonify({
        'videos': videos,
        'nextPageToken': next_page if not config.DEV_MODE else None  # Disable pagination in dev
    })


@app.route('/api/channel/search', methods=['GET'])
def search_videos():
    query = request.args.get('q', '')
    page_token = request.args.get('pageToken')
    if not config.RAF_TALKS_CHANNEL_ID:
        return jsonify({'error': 'Channel ID not set'}), 400
    
    max_results = config.DEV_VIDEO_LIMIT if config.DEV_MODE else 50
    
    videos, next_page = yt.search_channel(
        config.RAF_TALKS_CHANNEL_ID, 
        query, 
        max_results=max_results,
        page_token=page_token
    )
    return jsonify({
        'videos': videos,
        'nextPageToken': next_page if not config.DEV_MODE else None
    })


@app.route('/api/transcript', methods=['POST'])
def extract_transcript():
    data = request.json
    video_ids = data.get('video_ids', [])
    if not video_ids:
        return jsonify({'error': 'No video IDs provided'}), 400
    
    results = transcriber.extract_batch(video_ids)
    return jsonify({'results': results})


@app.route('/api/languages', methods=['GET'])
def get_languages():
    return jsonify({'languages': TranslationService.get_languages()})


# ===== MODEL SWITCHING ENDPOINTS =====

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available AI models and current selection."""
    return jsonify({
        'models': TranslationService.get_available_models(),
        'current': TranslationService.get_current_model()
    })


@app.route('/api/models/switch', methods=['POST'])
def switch_model():
    """Switch to a different AI model."""
    data = request.json
    model_name = data.get('model', '')
    
    if not model_name:
        return jsonify({'success': False, 'error': 'No model specified'}), 400
    
    if TranslationService.set_current_model(model_name):
        return jsonify({
            'success': True, 
            'current': model_name,
            'message': f'Switched to {model_name}'
        })
    else:
        return jsonify({
            'success': False, 
            'error': f'Unknown model: {model_name}'
        }), 400


@app.route('/api/translate', methods=['POST'])
def translate_text():
    data = request.json
    text = data.get('text', '')
    target_lang = data.get('target_lang', 'es')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    result = translator.translate(text, target_lang)
    return jsonify(result)


@app.route('/api/generate-production', methods=['POST'])
def generate_production():
    """Generate production-ready output: Spanish title, description, and tags in ONE API call."""
    data = request.json
    title = data.get('title', '')
    english_text = data.get('english_text', '')
    
    if not english_text:
        return jsonify({'error': 'No English text provided'}), 400
    
    try:
        import json
        
        # Get current model and its provider
        current_model = TranslationService.get_current_model()
        model_info = config.AVAILABLE_MODELS.get(current_model, {})
        provider = model_info.get('provider', 'google')
        
        # Single combined prompt for all outputs
        combined_prompt = f"""Generate YouTube production content in Spanish for this football video.

ORIGINAL TITLE: {title}

ENGLISH CONTENT: {english_text[:1000]}

Return EXACTLY this JSON format (no markdown, no code blocks, just raw JSON):
{{
    "title": "🚨 SPANISH TITLE IN ALL CAPS HERE",
    "description": "Long SEO description here with emojis and hashtags at end",
    "tags": "tag1, tag2, tag3, tag4, tag5"
}}

RULES FOR EACH FIELD:
- TITLE: Translate to Spanish, add 🚨 at start, ALL UPPERCASE letters
- DESCRIPTION: 5-8 sentences, SEO-optimized, include emojis, hashtags at end (lowercase like #futbol #barcelona), NO bold/markdown formatting
- TAGS: 10-15 tags separated by commas, all lowercase, include player names, team names, relevant topics

Return ONLY the JSON, nothing else."""

        # Call appropriate API based on provider
        if provider == 'groq':
            # Use Groq API
            if not config.GROQ_API_KEY:
                return jsonify({'success': False, 'error': 'Groq API key not configured'})
            
            from groq import Groq
            groq_client = Groq(api_key=config.GROQ_API_KEY)
            
            completion = groq_client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": combined_prompt}],
                temperature=0.7,
                max_completion_tokens=2048,
                stream=False
            )
            response_text = completion.choices[0].message.content.strip()
        else:
            # Use Gemini/Gemma API
            from google import genai
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model=current_model,
                contents=combined_prompt
            )
            response_text = response.text.strip()
        
        # Remove any markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        return jsonify({
            'success': True,
            'title': result.get('title', ''),
            'description': result.get('description', ''),
            'tags': result.get('tags', ''),
            'model_used': current_model
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Failed to parse AI response: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)

