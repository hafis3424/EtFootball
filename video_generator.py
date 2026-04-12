"""
Video Generator Module
Uses FFmpeg to combine a static thumbnail image + voiceover audio into an MP4 video.
"""

import os
import base64
import tempfile
import subprocess
import time
import json
from mutagen.mp3 import MP3


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output', 'videos')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global progress state
_video_progress = {}


def get_progress(task_id):
    """Get the current progress of a video creation task."""
    return _video_progress.get(task_id, {
        'status': 'unknown',
        'progress': 0,
        'message': 'Task not found'
    })


def _update_progress(task_id, status, progress, message='', **kwargs):
    """Update progress for a task."""
    _video_progress[task_id] = {
        'status': status,
        'progress': progress,
        'message': message,
        **kwargs
    }


def get_audio_duration(audio_path):
    """Get duration of an MP3 file in seconds."""
    try:
        audio = MP3(audio_path)
        return audio.info.length
    except Exception:
        # Fallback: use ffprobe
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_format', audio_path],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception:
            return 0


def create_video(image_base64, audio_path, output_name=None, task_id=None):
    """
    Create an MP4 video from a static thumbnail image and voiceover audio.
    
    Args:
        image_base64: Base64-encoded PNG image (with or without data URL prefix)
        audio_path: Path to the MP3 voiceover audio file
        output_name: Optional output filename (without extension)
        task_id: Optional task ID for progress tracking
    
    Returns:
        dict with success status, output path, duration, etc.
    """
    if not output_name:
        output_name = f"video_{int(time.time())}"
    
    output_path = os.path.join(OUTPUT_DIR, f"{output_name}.mp4")
    
    if task_id:
        _update_progress(task_id, 'preparing', 10, 'Preparing image...')
    
    try:
        # 1. Decode base64 image to temp file
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_bytes = base64.b64decode(image_base64)
        
        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
            tmp_img.write(image_bytes)
            tmp_image_path = tmp_img.name
        
        # 2. Get audio duration
        duration = get_audio_duration(audio_path)
        if duration <= 0:
            return {'success': False, 'error': 'Could not determine audio duration'}
        
        if task_id:
            _update_progress(task_id, 'encoding', 30, 
                           f'Creating video ({duration:.1f}s)...')
        
        # 3. FFmpeg: combine static image + audio → MP4
        # -loop 1: loop the image
        # -t: duration matches audio
        # -c:v libx264: H.264 video codec
        # -tune stillimage: optimize for static image
        # -c:a aac: AAC audio codec
        # -b:a 192k: audio bitrate
        # -pix_fmt yuv420p: pixel format for compatibility
        # -shortest: end when shortest stream ends
        # -vf scale: ensure dimensions are even (required by H.264)
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', tmp_image_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-shortest',
            '-t', str(duration),
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Clean up temp image
        try:
            os.unlink(tmp_image_path)
        except Exception:
            pass
        
        if result.returncode != 0:
            error_msg = result.stderr[-500:] if result.stderr else 'Unknown FFmpeg error'
            if task_id:
                _update_progress(task_id, 'error', 0, f'FFmpeg error: {error_msg}')
            return {'success': False, 'error': f'FFmpeg error: {error_msg}'}
        
        # 4. Get output file size
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        if task_id:
            _update_progress(task_id, 'done', 100, 'Video created!',
                           output_path=output_path,
                           output_name=f"{output_name}.mp4",
                           duration=duration,
                           file_size_mb=file_size_mb)
        
        return {
            'success': True,
            'output_path': output_path,
            'output_name': f"{output_name}.mp4",
            'duration': duration,
            'file_size_mb': file_size_mb
        }
        
    except subprocess.TimeoutExpired:
        if task_id:
            _update_progress(task_id, 'error', 0, 'Video creation timed out')
        return {'success': False, 'error': 'Video creation timed out (>5 minutes)'}
    except Exception as e:
        if task_id:
            _update_progress(task_id, 'error', 0, str(e))
        return {'success': False, 'error': str(e)}


def list_videos():
    """List all generated videos in the output directory."""
    videos = []
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR), reverse=True):
            if f.endswith('.mp4'):
                path = os.path.join(OUTPUT_DIR, f)
                size = os.path.getsize(path)
                videos.append({
                    'name': f,
                    'path': path,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'created': os.path.getctime(path)
                })
    return videos
