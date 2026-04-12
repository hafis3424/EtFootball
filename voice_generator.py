"""
Voice Generator Module
Uses Microsoft Edge TTS (edge-tts) for high-quality voiceover generation.
Supports 322+ voices, auto-chunking for long texts, and progress tracking.
"""

import edge_tts
import asyncio
import os
import re
import tempfile
import time
from mutagen.mp3 import MP3


# ===== CONFIGURATION =====
CHUNK_SIZE = 4500          # Characters per edge-tts request (~5000 limit)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output', 'audio')
DEFAULT_VOICE = 'es-MX-DaliaNeural'  # Spanish female (natural-sounding)
DEFAULT_RATE = '+0%'
DEFAULT_PITCH = '+0Hz'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===== VOICE CACHE =====
_voices_cache = None


# Language code to human-readable name mapping
LANG_NAMES = {
    'af': 'Afrikaans', 'am': 'Amharic', 'ar': 'Arabic', 'az': 'Azerbaijani',
    'bg': 'Bulgarian', 'bn': 'Bangla', 'bs': 'Bosnian', 'ca': 'Catalan',
    'cs': 'Czech', 'cy': 'Welsh', 'da': 'Danish', 'de': 'German',
    'el': 'Greek', 'en': 'English', 'es': 'Spanish', 'et': 'Estonian',
    'eu': 'Basque', 'fa': 'Persian', 'fi': 'Finnish', 'fil': 'Filipino',
    'fr': 'French', 'ga': 'Irish', 'gl': 'Galician', 'gu': 'Gujarati',
    'he': 'Hebrew', 'hi': 'Hindi', 'hr': 'Croatian', 'hu': 'Hungarian',
    'hy': 'Armenian', 'id': 'Indonesian', 'is': 'Icelandic', 'it': 'Italian',
    'ja': 'Japanese', 'jv': 'Javanese', 'ka': 'Georgian', 'kk': 'Kazakh',
    'km': 'Khmer', 'kn': 'Kannada', 'ko': 'Korean', 'lo': 'Lao',
    'lt': 'Lithuanian', 'lv': 'Latvian', 'mk': 'Macedonian', 'ml': 'Malayalam',
    'mn': 'Mongolian', 'mr': 'Marathi', 'ms': 'Malay', 'mt': 'Maltese',
    'my': 'Myanmar', 'nb': 'Norwegian', 'ne': 'Nepali', 'nl': 'Dutch',
    'pa': 'Punjabi', 'pl': 'Polish', 'ps': 'Pashto', 'pt': 'Portuguese',
    'ro': 'Romanian', 'ru': 'Russian', 'si': 'Sinhala', 'sk': 'Slovak',
    'sl': 'Slovenian', 'so': 'Somali', 'sq': 'Albanian', 'sr': 'Serbian',
    'su': 'Sundanese', 'sv': 'Swedish', 'sw': 'Swahili', 'ta': 'Tamil',
    'te': 'Telugu', 'th': 'Thai', 'tr': 'Turkish', 'uk': 'Ukrainian',
    'ur': 'Urdu', 'uz': 'Uzbek', 'vi': 'Vietnamese', 'zh': 'Chinese',
    'zu': 'Zulu'
}

REGION_NAMES = {
    'US': 'US', 'GB': 'UK', 'AU': 'Australia', 'CA': 'Canada',
    'IN': 'India', 'MX': 'Mexico', 'ES': 'Spain', 'BR': 'Brazil',
    'FR': 'France', 'DE': 'Germany', 'IT': 'Italy', 'JP': 'Japan',
    'KR': 'Korea', 'CN': 'China', 'TW': 'Taiwan', 'HK': 'Hong Kong',
    'SG': 'Singapore', 'PH': 'Philippines', 'MY': 'Malaysia',
    'ID': 'Indonesia', 'TH': 'Thailand', 'VN': 'Vietnam',
    'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru',
    'VE': 'Venezuela', 'CU': 'Cuba', 'DO': 'Dominican Republic',
    'EC': 'Ecuador', 'GQ': 'Equatorial Guinea', 'GT': 'Guatemala',
    'HN': 'Honduras', 'NI': 'Nicaragua', 'PA': 'Panama', 'PR': 'Puerto Rico',
    'PY': 'Paraguay', 'SV': 'El Salvador', 'UY': 'Uruguay', 'BO': 'Bolivia',
    'CR': 'Costa Rica', 'PT': 'Portugal', 'AE': 'UAE', 'SA': 'Saudi Arabia',
    'EG': 'Egypt', 'DZ': 'Algeria', 'BH': 'Bahrain', 'IQ': 'Iraq',
    'JO': 'Jordan', 'KW': 'Kuwait', 'LB': 'Lebanon', 'LY': 'Libya',
    'MA': 'Morocco', 'OM': 'Oman', 'QA': 'Qatar', 'SY': 'Syria',
    'TN': 'Tunisia', 'YE': 'Yemen', 'ZA': 'South Africa',
    'NG': 'Nigeria', 'KE': 'Kenya', 'TZ': 'Tanzania', 'ET': 'Ethiopia',
    'IE': 'Ireland', 'NZ': 'New Zealand', 'AT': 'Austria', 'CH': 'Switzerland',
    'BE': 'Belgium', 'NL': 'Netherlands', 'SE': 'Sweden', 'NO': 'Norway',
    'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland', 'CZ': 'Czech Republic',
    'RO': 'Romania', 'GR': 'Greece', 'TR': 'Turkey', 'RU': 'Russia',
    'UA': 'Ukraine', 'IL': 'Israel', 'PK': 'Pakistan', 'BD': 'Bangladesh',
    'LK': 'Sri Lanka', 'MM': 'Myanmar', 'KH': 'Cambodia', 'LA': 'Laos',
    'NP': 'Nepal', 'AF': 'Afghanistan', 'GE': 'Georgia', 'AM': 'Armenia',
    'AZ': 'Azerbaijan', 'KZ': 'Kazakhstan', 'UZ': 'Uzbekistan',
    'RS': 'Serbia', 'BA': 'Bosnia', 'MK': 'North Macedonia',
    'BG': 'Bulgaria', 'HR': 'Croatia', 'SK': 'Slovakia', 'SI': 'Slovenia',
    'HU': 'Hungary', 'LT': 'Lithuania', 'LV': 'Latvia', 'EE': 'Estonia',
    'MT': 'Malta', 'IS': 'Iceland', 'CY': 'Cyprus'
}

# Best Spanish voices for football content
RECOMMENDED_VOICES = {
    'es-MX-DaliaNeural': {'tier': 'ultra', 'style': 'Storyteller', 'note': 'Natural Mexican Spanish, great for narration'},
    'es-ES-ElviraNeural': {'tier': 'ultra', 'style': 'Professional', 'note': 'Clean European Spanish'},
    'es-AR-ElenaNeural': {'tier': 'good', 'style': 'Energetic', 'note': 'Argentine Spanish with energy'},
    'es-CO-SalomeNeural': {'tier': 'good', 'style': 'Calm', 'note': 'Colombian accent, warm tone'},
    'es-MX-JorgeNeural': {'tier': 'ultra', 'style': 'Storyteller', 'note': 'Male, authoritative narration'},
    'es-ES-AlvaroNeural': {'tier': 'good', 'style': 'Professional', 'note': 'Male, European Spanish'},
}


def _extract_voice_name(short_name):
    """Extract clean voice name from edge-tts ShortName like 'es-MX-DaliaNeural'."""
    parts = short_name.split('-')
    if len(parts) >= 3:
        name = parts[2].replace('Neural', '').replace('Multilingual', '')
        return name
    return short_name


def _organize_voices(voices):
    """Organize raw voice data into {language: [voice_objects]} structure."""
    organized = {}
    
    for voice in voices:
        locale = voice['Locale']
        lang_code = locale.split('-')[0]
        region = locale.split('-')[1] if '-' in locale else ''
        
        lang_name = LANG_NAMES.get(lang_code, locale)
        region_name = REGION_NAMES.get(region, region)
        
        name = _extract_voice_name(voice['ShortName'])
        is_recommended = voice['ShortName'] in RECOMMENDED_VOICES
        rec_info = RECOMMENDED_VOICES.get(voice['ShortName'], {})
        
        voice_obj = {
            'id': voice['ShortName'],
            'name': name,
            'gender': voice['Gender'],
            'locale': locale,
            'region': region_name,
            'display': f"{name} ({region_name})",
            'recommended': is_recommended,
            'tier': rec_info.get('tier', ''),
            'style': rec_info.get('style', ''),
            'note': rec_info.get('note', '')
        }
        
        if lang_name not in organized:
            organized[lang_name] = []
        organized[lang_name].append(voice_obj)
    
    # Sort voices within each language (recommended first, then alphabetical)
    for lang in organized:
        organized[lang].sort(key=lambda x: (
            0 if x['recommended'] else 1,
            x['name'],
            x['region']
        ))
    
    return dict(sorted(organized.items()))


async def _get_all_voices():
    """Fetch all available voices from edge-tts (async)."""
    global _voices_cache
    if _voices_cache is not None:
        return _voices_cache
    
    voices = await edge_tts.list_voices()
    _voices_cache = _organize_voices(voices)
    return _voices_cache


def get_voices_sync():
    """Synchronous wrapper to get all voices (for Flask routes)."""
    return asyncio.run(_get_all_voices())


def get_voice_count():
    """Get total voice and language count."""
    voices = get_voices_sync()
    total_voices = sum(len(v) for v in voices.values())
    total_languages = len(voices)
    return total_voices, total_languages


# ===== TEXT CHUNKING =====

def _split_into_chunks(text, chunk_size=CHUNK_SIZE):
    """Split text into chunks at sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current = ''
    
    # Split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = (current + ' ' + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # Handle single sentences longer than chunk_size
            if len(sentence) > chunk_size:
                # Split at word boundaries
                words = sentence.split()
                current = ''
                for word in words:
                    if len(current) + len(word) + 1 <= chunk_size:
                        current = (current + ' ' + word).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = sentence
    
    if current:
        chunks.append(current)
    
    return chunks


# ===== PROGRESS TRACKING =====

# Global progress state for background tasks
_generation_progress = {}


def get_progress(task_id):
    """Get the current progress of a generation task."""
    return _generation_progress.get(task_id, {
        'status': 'unknown',
        'progress': 0,
        'message': 'Task not found'
    })


def _update_progress(task_id, status, progress, message='', **kwargs):
    """Update progress for a task."""
    _generation_progress[task_id] = {
        'status': status,
        'progress': progress,
        'message': message,
        **kwargs
    }


# ===== VOICEOVER GENERATION =====

async def _generate_chunk(text, voice, rate, pitch, output_path):
    """Generate a single audio chunk."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


async def _generate_voiceover_async(text, voice=DEFAULT_VOICE, rate=DEFAULT_RATE, 
                                      pitch=DEFAULT_PITCH, output_name=None, task_id=None):
    """Generate voiceover audio (async implementation)."""
    if not output_name:
        output_name = f"voiceover_{int(time.time())}"
    
    output_path = os.path.join(OUTPUT_DIR, f"{output_name}.mp3")
    
    # Split text into chunks
    chunks = _split_into_chunks(text)
    total_chunks = len(chunks)
    
    if task_id:
        _update_progress(task_id, 'generating', 0, 
                        f'Starting generation ({total_chunks} chunk{"s" if total_chunks > 1 else ""})')
    
    if total_chunks == 1:
        # Single chunk — direct generation
        if task_id:
            _update_progress(task_id, 'generating', 50, 'Generating audio...')
        
        await _generate_chunk(chunks[0], voice, rate, pitch, output_path)
    else:
        # Multiple chunks — generate and merge
        chunk_files = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(tmpdir, f"chunk_{i}.mp3")
                
                if task_id:
                    progress = int((i / total_chunks) * 90)
                    _update_progress(task_id, 'generating', progress,
                                   f'Generating chunk {i+1} of {total_chunks}')
                
                await _generate_chunk(chunk, voice, rate, pitch, chunk_path)
                chunk_files.append(chunk_path)
            
            if task_id:
                _update_progress(task_id, 'merging', 90, 'Merging audio chunks...')
            
            # Merge all chunks using binary concatenation (MP3 is frame-based)
            with open(output_path, 'wb') as outfile:
                for chunk_file in chunk_files:
                    with open(chunk_file, 'rb') as infile:
                        outfile.write(infile.read())
    
    # Get duration
    try:
        audio = MP3(output_path)
        duration = audio.info.length
    except Exception:
        duration = 0
    
    if task_id:
        _update_progress(task_id, 'done', 100, 'Voiceover generated!',
                        output_path=output_path,
                        output_name=f"{output_name}.mp3",
                        duration=duration)
    
    return {
        'success': True,
        'output_path': output_path,
        'output_name': f"{output_name}.mp3",
        'duration': duration,
        'chunks': total_chunks
    }


def generate_voiceover(text, voice=DEFAULT_VOICE, rate=DEFAULT_RATE,
                       pitch=DEFAULT_PITCH, output_name=None, task_id=None):
    """Generate voiceover audio (synchronous wrapper)."""
    return asyncio.run(
        _generate_voiceover_async(text, voice, rate, pitch, output_name, task_id)
    )


async def _generate_preview_async(text, voice=DEFAULT_VOICE, rate=DEFAULT_RATE, pitch=DEFAULT_PITCH):
    """Generate a short preview clip (first ~100 chars)."""
    preview_text = text[:150].rsplit(' ', 1)[0] if len(text) > 150 else text
    
    preview_path = os.path.join(OUTPUT_DIR, f"preview_{int(time.time())}.mp3")
    
    communicate = edge_tts.Communicate(preview_text, voice, rate=rate, pitch=pitch)
    await communicate.save(preview_path)
    
    return {
        'success': True,
        'output_path': preview_path
    }


def generate_preview(text, voice=DEFAULT_VOICE, rate=DEFAULT_RATE, pitch=DEFAULT_PITCH):
    """Generate a short preview clip (synchronous)."""
    return asyncio.run(_generate_preview_async(text, voice, rate, pitch))
