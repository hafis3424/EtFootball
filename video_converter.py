"""
Video Converter Module
Handles video format conversion and utilities for Phase 6 & 7.

- Thumbnail extraction from video files (FFmpeg)
- Video info extraction (ffprobe)
- Center-crop 16:9 → 9:16 for social media platforms
- Directory listing for HeyGen imports and social outputs
"""

import os
import subprocess
import json
import time
import threading


# ===== CONFIGURATION =====
HEYGEN_DIR = os.path.join(os.path.dirname(__file__), 'output', 'heygen')
SOCIAL_DIR = os.path.join(os.path.dirname(__file__), 'output', 'social')
THUMB_DIR = os.path.join(os.path.dirname(__file__), 'output', 'heygen_thumbs')

# Ensure directories exist
os.makedirs(HEYGEN_DIR, exist_ok=True)
os.makedirs(SOCIAL_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

# Portrait output resolution (standard for Reels/Shorts/TikTok)
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920

# ===== PROGRESS TRACKING =====
_progress = {}
_progress_lock = threading.Lock()


def _update_progress(task_id, progress, status, message, **kwargs):
    """Update progress for a conversion task."""
    with _progress_lock:
        _progress[task_id] = {
            'progress': progress,
            'status': status,
            'message': message,
            **kwargs,
            'updated_at': time.time()
        }


def get_progress(task_id):
    """Get the current progress of a conversion task."""
    with _progress_lock:
        return _progress.get(task_id, {
            'progress': 0,
            'status': 'unknown',
            'message': 'No task found'
        })


# ===== VIDEO INFO =====

def get_video_info(video_path):
    """Get video duration, resolution, and file size using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', video_path],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        data = json.loads(result.stdout)

        # Find video stream
        video_stream = next(
            (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
            {}
        )

        # Parse frame rate safely
        fps = 0
        r_frame_rate = video_stream.get('r_frame_rate', '0/1')
        if '/' in r_frame_rate:
            parts = r_frame_rate.split('/')
            if len(parts) == 2 and int(parts[1]) != 0:
                fps = round(int(parts[0]) / int(parts[1]), 2)
        else:
            try:
                fps = float(r_frame_rate)
            except (ValueError, TypeError):
                fps = 0

        file_size = int(data.get('format', {}).get('size', 0))

        return {
            'duration': float(data.get('format', {}).get('duration', 0)),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'codec': video_stream.get('codec_name', 'unknown'),
            'fps': fps
        }
    except Exception as e:
        return {
            'duration': 0, 'width': 0, 'height': 0,
            'file_size': 0, 'file_size_mb': 0,
            'codec': 'unknown', 'fps': 0,
            'error': str(e)
        }


# ===== THUMBNAIL EXTRACTION =====

def extract_thumbnail(video_path, output_path=None):
    """Extract the first frame of a video as a JPEG thumbnail."""
    if output_path is None:
        basename = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(THUMB_DIR, f"{basename}.jpg")

    # Return cached thumbnail if it exists
    if os.path.exists(output_path):
        return output_path

    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-vf', 'scale=640:-1',
            output_path
        ]

        subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"Thumbnail extraction failed: {e}")

    return None


# ===== CENTER-CROP CONVERSION (16:9 → 9:16) =====

def convert_to_portrait(input_path, output_name=None, task_id=None):
    """
    Convert a 16:9 landscape video to 9:16 portrait using center-crop.

    Takes the center vertical portion of the video, cropping the sides.
    Output: 1080x1920 MP4 (standard for Instagram Reels, TikTok, Shorts).
    """
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_9x16"

    output_path = os.path.join(SOCIAL_DIR, f"{output_name}.mp4")

    if task_id:
        _update_progress(task_id, 10, 'preparing', 'Analyzing video...')

    try:
        # Get input video info
        info = get_video_info(input_path)
        duration = info['duration']

        if task_id:
            _update_progress(task_id, 20, 'converting',
                             f'Converting to 9:16 ({duration:.1f}s video)...')

        # Center-crop filter:
        # 1. crop=ih*9/16:ih — crops width to 9:16 ratio from center
        # 2. scale=1080:1920 — scales to standard portrait resolution
        filter_chain = f"crop=ih*9/16:ih,scale={PORTRAIT_WIDTH}:{PORTRAIT_HEIGHT}"

        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vf', filter_chain,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            output_path
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            error_msg = result.stderr[-500:] if result.stderr else 'Unknown FFmpeg error'
            if task_id:
                _update_progress(task_id, 0, 'error', f'Conversion failed: {error_msg}')
            return {'success': False, 'error': error_msg}

        # Get output info
        output_info = get_video_info(output_path)

        if task_id:
            _update_progress(task_id, 100, 'done', 'Conversion complete!',
                             output_path=output_path,
                             output_name=f"{output_name}.mp4",
                             duration=output_info['duration'],
                             file_size_mb=output_info['file_size_mb'])

        return {
            'success': True,
            'output_path': output_path,
            'output_name': f"{output_name}.mp4",
            'duration': output_info['duration'],
            'file_size_mb': output_info['file_size_mb'],
            'width': output_info['width'],
            'height': output_info['height']
        }

    except subprocess.TimeoutExpired:
        if task_id:
            _update_progress(task_id, 0, 'error', 'Conversion timed out (>10 min)')
        return {'success': False, 'error': 'Conversion timed out'}
    except Exception as e:
        if task_id:
            _update_progress(task_id, 0, 'error', str(e))
        return {'success': False, 'error': str(e)}


# ===== DIRECTORY LISTING =====

def list_heygen_videos():
    """List all videos in the HeyGen import directory."""
    videos = []
    if os.path.exists(HEYGEN_DIR):
        for f in sorted(os.listdir(HEYGEN_DIR)):
            if f.lower().endswith(('.mp4', '.mov', '.webm')):
                path = os.path.join(HEYGEN_DIR, f)
                info = get_video_info(path)
                thumb = extract_thumbnail(path)
                videos.append({
                    'filename': f,
                    'path': path,
                    'duration': info['duration'],
                    'width': info['width'],
                    'height': info['height'],
                    'file_size_mb': info['file_size_mb'],
                    'has_thumbnail': thumb is not None,
                    'created': os.path.getctime(path)
                })
    return videos


def list_social_videos():
    """List all converted 9:16 videos."""
    videos = []
    if os.path.exists(SOCIAL_DIR):
        for f in sorted(os.listdir(SOCIAL_DIR)):
            if f.lower().endswith(('.mp4', '.mov')):
                path = os.path.join(SOCIAL_DIR, f)
                info = get_video_info(path)
                videos.append({
                    'filename': f,
                    'path': path,
                    'duration': info['duration'],
                    'width': info['width'],
                    'height': info['height'],
                    'file_size_mb': info['file_size_mb'],
                    'created': os.path.getctime(path)
                })
    return videos
