"""
YouTube Uploader Module
Handles OAuth2 authentication and video uploading to YouTube.
Uses YouTube Data API v3 with resumable uploads and progress tracking.
"""

import os
import json
import time
import threading
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ===== CONFIG =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, 'client_secret.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# YouTube upload scope
SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube']

# Default upload settings
DEFAULT_CATEGORY = '17'  # Sports
DEFAULT_LANGUAGE = 'es'  # Spanish
DEFAULT_PRIVACY = 'private'  # Private by default (scheduled uploads must be private first)

# Progress tracking
_progress = {}
_progress_lock = threading.Lock()


def check_auth_status():
    """Check if OAuth2 is configured and credentials are valid."""
    result = {
        'has_client_secret': os.path.exists(CLIENT_SECRET_FILE),
        'has_token': os.path.exists(TOKEN_FILE),
        'is_authenticated': False,
        'channel_name': None,
        'channel_id': None
    }
    
    if not result['has_client_secret']:
        result['message'] = 'client_secret.json not found. Please download OAuth credentials from Google Cloud Console.'
        return result
    
    if result['has_token']:
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                result['is_authenticated'] = True
                # Get channel info
                youtube = build('youtube', 'v3', credentials=creds)
                response = youtube.channels().list(part='snippet', mine=True).execute()
                if response.get('items'):
                    channel = response['items'][0]
                    result['channel_name'] = channel['snippet']['title']
                    result['channel_id'] = channel['id']
                result['message'] = f'Connected as: {result["channel_name"]}'
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(TOKEN_FILE, 'w') as f:
                    f.write(creds.to_json())
                result['is_authenticated'] = True
                result['message'] = 'Token refreshed successfully'
            else:
                result['message'] = 'Token expired. Please re-authorize.'
        except Exception as e:
            result['message'] = f'Token error: {str(e)}'
    else:
        result['message'] = 'Not authorized yet. Click "Connect YouTube" to authorize.'
    
    return result


def authorize():
    """Start OAuth2 authorization flow. Opens browser for consent."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        return {'success': False, 'error': 'client_secret.json not found'}
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        # This opens a browser window for the user to authorize
        creds = flow.run_local_server(port=8090, prompt='consent')
        
        # Save credentials
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        
        # Get channel info
        youtube = build('youtube', 'v3', credentials=creds)
        response = youtube.channels().list(part='snippet', mine=True).execute()
        channel_name = ''
        if response.get('items'):
            channel_name = response['items'][0]['snippet']['title']
        
        return {
            'success': True,
            'message': f'Successfully connected to: {channel_name}',
            'channel_name': channel_name
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _get_authenticated_service():
    """Get an authenticated YouTube API service."""
    if not os.path.exists(TOKEN_FILE):
        raise Exception('Not authenticated. Please authorize first.')
    
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
        else:
            raise Exception('Token expired. Please re-authorize.')
    
    return build('youtube', 'v3', credentials=creds)


def upload_video(video_path, title, description, tags, privacy='private',
                 publish_at=None, thumbnail_path=None, task_id=None):
    """
    Upload a video to YouTube with metadata.
    
    Args:
        video_path: Path to the MP4 file
        title: Video title
        description: Video description
        tags: List of tags
        privacy: 'private', 'unlisted', or 'public'
        publish_at: ISO 8601 datetime string for scheduled publishing (e.g., '2026-04-15T14:00:00Z')
        thumbnail_path: Path to thumbnail image (optional)
        task_id: Task ID for progress tracking
    """
    if task_id:
        _update_progress(task_id, 0, 'starting', 'Preparing upload...')
    
    try:
        youtube = _get_authenticated_service()
        
        if not os.path.exists(video_path):
            raise Exception(f'Video file not found: {video_path}')
        
        # Build video metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube max title length
                'description': description[:5000],  # YouTube max description length
                'tags': tags if isinstance(tags, list) else [t.strip() for t in tags.split(',')],
                'categoryId': DEFAULT_CATEGORY,
                'defaultLanguage': DEFAULT_LANGUAGE,
                'defaultAudioLanguage': DEFAULT_LANGUAGE
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Handle scheduled publishing
        if publish_at:
            # Scheduled uploads must be private first, YouTube auto-publishes at the scheduled time
            body['status']['privacyStatus'] = 'private'
            body['status']['publishAt'] = publish_at
        
        if task_id:
            _update_progress(task_id, 5, 'uploading', 'Starting upload...')
        
        # Create resumable upload
        file_size = os.path.getsize(video_path)
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024 * 1024 * 5  # 5MB chunks
        )
        
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        # Execute upload with progress tracking
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress_pct = int(status.progress() * 85) + 5  # 5-90%
                uploaded_mb = (status.resumable_progress / (1024 * 1024))
                total_mb = (file_size / (1024 * 1024))
                if task_id:
                    _update_progress(
                        task_id, progress_pct, 'uploading',
                        f'Uploading: {uploaded_mb:.1f} / {total_mb:.1f} MB'
                    )
        
        video_id = response.get('id')
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        
        if task_id:
            _update_progress(task_id, 90, 'processing', 'Upload complete, processing...')
        
        # Set custom thumbnail if provided
        thumbnail_set = False
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype='image/png')
                ).execute()
                thumbnail_set = True
            except HttpError as e:
                # Thumbnail upload may fail if channel isn't verified
                print(f'Thumbnail upload failed (channel may need verification): {e}')
        
        result = {
            'success': True,
            'video_id': video_id,
            'video_url': video_url,
            'title': title,
            'privacy': body['status']['privacyStatus'],
            'scheduled': publish_at,
            'thumbnail_set': thumbnail_set
        }
        
        if task_id:
            _update_progress(task_id, 100, 'done', 'Upload complete!', result=result)
        
        return result
        
    except HttpError as e:
        error_msg = f'YouTube API error: {e.resp.status} - {e.content.decode()}'
        if task_id:
            _update_progress(task_id, 0, 'error', error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = str(e)
        if task_id:
            _update_progress(task_id, 0, 'error', error_msg)
        return {'success': False, 'error': error_msg}


def save_thumbnail_from_base64(base64_data, filename='upload_thumbnail.png'):
    """Save a base64-encoded image to a file for thumbnail upload."""
    import base64
    
    output_dir = os.path.join(BASE_DIR, 'output', 'thumbnails')
    os.makedirs(output_dir, exist_ok=True)
    
    # Remove data URL prefix if present
    if ',' in base64_data:
        base64_data = base64_data.split(',')[1]
    
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(base64.b64decode(base64_data))
    
    return filepath


# ===== PROGRESS TRACKING =====
def _update_progress(task_id, progress, status, message, result=None):
    with _progress_lock:
        _progress[task_id] = {
            'progress': progress,
            'status': status,
            'message': message,
            'result': result,
            'updated_at': time.time()
        }


def get_progress(task_id):
    with _progress_lock:
        return _progress.get(task_id, {
            'progress': 0,
            'status': 'unknown',
            'message': 'No task found'
        })


def cleanup_old_progress(max_age=3600):
    """Remove progress entries older than max_age seconds."""
    with _progress_lock:
        now = time.time()
        to_remove = [k for k, v in _progress.items() 
                     if now - v.get('updated_at', 0) > max_age]
        for k in to_remove:
            del _progress[k]
