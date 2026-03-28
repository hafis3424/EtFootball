import requests
import re
import subprocess
import json
import os
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi


class TranscriptExtractor:
    """
    Extracts YouTube transcripts using youtube-transcript-api (primary)
    with InnerTube API fallback.
    """
    
    def __init__(self):
        self.api = YouTubeTranscriptApi()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _get_title(self, video_id):
        """Fetch video title from YouTube page."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(url, timeout=10)
            match = re.search(r'<title>(.*?)(?:\s*-\s*YouTube)?\s*</title>', response.text)
            if match:
                import html
                return html.unescape(match.group(1)).strip()
        except Exception:
            pass
        return 'Unknown Title'
    
    def _extract_with_library(self, video_id):
        """Primary method: Use youtube-transcript-api library (v1.2+)."""
        # First, list available transcripts to find the best one
        transcript_list = list(self.api.list(video_id))
        
        if not transcript_list:
            raise Exception("No transcripts available")
        
        # Collect all available language codes
        available_langs = [t.language_code for t in transcript_list]
        
        # Preferred language order
        preferred = ['en', 'ml', 'hi', 'ta', 'te', 'kn']
        
        # Find best matching language
        lang_to_use = None
        for lang in preferred:
            if lang in available_langs:
                lang_to_use = lang
                break
        
        # If none of preferred found, use first available
        if lang_to_use is None:
            lang_to_use = available_langs[0]
        
        # Fetch the transcript
        result = self.api.fetch(video_id, languages=[lang_to_use])
        
        # Extract text from snippets
        lines = [snippet.text for snippet in result]
        return '\n'.join(lines)
    
    def _extract_with_ytdlp(self, video_id):
        """Fallback method: Use yt-dlp to extract subtitles (better rate-limit handling)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = os.path.join(tmpdir, "sub")
            
            # Try with different cookie sources, then without
            cookie_browsers = ['chrome', 'edge', 'firefox', None]
            
            for browser in cookie_browsers:
                cmd = [
                    'yt-dlp',
                    '--write-subs', '--write-auto-subs',
                    '--sub-langs', 'ml,en,hi,ta,te,kn',
                    '--skip-download',
                    '--sub-format', 'json3',
                    '-o', output_template,
                    '--no-warnings',
                    '--no-check-certificates',
                    f'https://www.youtube.com/watch?v={video_id}'
                ]
                
                if browser:
                    cmd.insert(1, '--cookies-from-browser')
                    cmd.insert(2, browser)
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    # Check if any subtitle files were created
                    sub_files = [f for f in os.listdir(tmpdir) if f.endswith('.json3')]
                    
                    if sub_files:
                        # Prefer Malayalam first (original language), then others
                        preferred_order = ['ml', 'en', 'hi', 'ta', 'te', 'kn']
                        selected_file = None
                        
                        for lang in preferred_order:
                            for f in sub_files:
                                if f'.{lang}.' in f:
                                    selected_file = f
                                    break
                            if selected_file:
                                break
                        
                        if not selected_file:
                            selected_file = sub_files[0]
                        
                        filepath = os.path.join(tmpdir, selected_file)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Parse json3 format
                        lines = []
                        for event in data.get('events', []):
                            segs = event.get('segs', [])
                            if segs:
                                text = ''.join(seg.get('utf8', '') for seg in segs).strip()
                                if text and text != '\n':
                                    lines.append(text)
                        
                        if lines:
                            return '\n'.join(lines)
                    
                    # Cookie error — try next browser
                    if browser and ('cookie' in result.stderr.lower() or 'Could not copy' in result.stderr):
                        continue
                    
                    # 429 without cookies — stop trying
                    if not browser and '429' in result.stderr:
                        break
                        
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
            
            raise Exception("yt-dlp could not extract subtitles")
    
    def _get_innertube_key(self, video_id):
        """Fetch the video page and extract INNERTUBE_API_KEY."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = self.session.get(url)
        response.raise_for_status()
        
        match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', response.text)
        if not match:
            raise Exception("Could not find INNERTUBE_API_KEY")
        return match.group(1)
    
    def _get_caption_tracks(self, video_id, api_key):
        """Call the player endpoint to get caption track URLs."""
        endpoint = f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
        
        # Try multiple clients in case one is blocked
        clients = [
            {
                "clientName": "IOS",
                "clientVersion": "19.09.3",
                "deviceModel": "iPhone14,3",
                "hl": "en",
                "gl": "US"
            },
            {
                "clientName": "ANDROID",
                "clientVersion": "19.09.37",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US"
            },
            {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US"
            }
        ]
        
        last_error = None
        for client in clients:
            try:
                payload = {
                    "context": {
                        "client": client
                    },
                    "videoId": video_id
                }
                
                response = self.session.post(endpoint, json=payload)
                response.raise_for_status()
                
                data = response.json()
                title = data.get('videoDetails', {}).get('title', 'Unknown Title')
                captions = data.get('captions', {})
                renderer = captions.get('playerCaptionsTracklistRenderer', {})
                tracks = renderer.get('captionTracks', [])
                
                if tracks:
                    return title, tracks
            except Exception as e:
                last_error = e
                continue
        
        if last_error:
            raise last_error
        raise Exception("No caption tracks found with any client")
    
    def _fetch_transcript_innertube(self, track_url):
        """Fetch and parse the transcript JSON from InnerTube."""
        if 'fmt=' in track_url:
            url = re.sub(r'fmt=[^&]+', 'fmt=json3', track_url)
        else:
            url = f"{track_url}&fmt=json3"
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        lines = []
        for event in data.get('events', []):
            segs = event.get('segs', [])
            if segs:
                text = ''.join(seg.get('utf8', '') for seg in segs).strip()
                if text:
                    lines.append(text)
        
        return '\n'.join(lines)
    
    def extract(self, video_id):
        """
        Extract transcript for a single video.
        Returns dict with video_id, title, transcript, success, error.
        """
        result = {
            'video_id': video_id,
            'title': '',
            'transcript': '',
            'success': False,
            'error': None
        }
        
        # Get title first
        result['title'] = self._get_title(video_id)
        
        # Method 1: youtube-transcript-api library (most reliable)
        try:
            transcript = self._extract_with_library(video_id)
            if transcript:
                result['transcript'] = transcript
                result['success'] = True
                return result
        except Exception as e:
            method1_error = str(e)
        
        # Method 2: yt-dlp fallback (handles rate-limiting better)
        try:
            transcript = self._extract_with_ytdlp(video_id)
            if transcript:
                result['transcript'] = transcript
                result['success'] = True
                return result
        except Exception as e:
            method2_error = str(e)
        
        # Method 3: InnerTube API with multiple client fallback
        try:
            api_key = self._get_innertube_key(video_id)
            title, tracks = self._get_caption_tracks(video_id, api_key)
            if title and title != 'Unknown Title':
                result['title'] = title
            
            if not tracks:
                result['error'] = 'No captions available for this video'
                return result
            
            tracks.sort(key=lambda t: (
                0 if t.get('languageCode') == 'en' else 1,
                0 if t.get('kind') != 'asr' else 1
            ))
            
            transcript = self._fetch_transcript_innertube(tracks[0]['baseUrl'])
            
            if not transcript:
                result['error'] = 'Transcript is empty'
                return result
            
            result['transcript'] = transcript
            result['success'] = True
            
        except Exception as e:
            result['error'] = f"All methods failed. Library: {method1_error} | yt-dlp: {method2_error} | InnerTube: {str(e)}"
        
        return result
    
    def extract_batch(self, video_ids):
        """Extract transcripts for multiple videos."""
        return [self.extract(vid) for vid in video_ids]
