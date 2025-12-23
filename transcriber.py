import requests
import re


class TranscriptExtractor:
    """
    Extracts YouTube transcripts using the InnerTube API.
    Ported from the working Chrome extension approach.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
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
        
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20251031.00.00"
                }
            },
            "videoId": video_id
        }
        
        response = self.session.post(endpoint, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Get video title
        title = data.get('videoDetails', {}).get('title', 'Unknown Title')
        
        # Get caption tracks
        captions = data.get('captions', {})
        renderer = captions.get('playerCaptionsTracklistRenderer', {})
        tracks = renderer.get('captionTracks', [])
        
        return title, tracks
    
    def _fetch_transcript(self, track_url):
        """Fetch and parse the transcript JSON."""
        # Add fmt=json3 to get JSON format
        url = f"{track_url}&fmt=json3"
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse events into clean text (same logic as extension)
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
        
        try:
            # Step 1: Get InnerTube API key
            api_key = self._get_innertube_key(video_id)
            
            # Step 2: Get caption tracks
            title, tracks = self._get_caption_tracks(video_id, api_key)
            result['title'] = title
            
            if not tracks:
                result['error'] = 'No captions available for this video'
                return result
            
            # Step 3: Sort tracks - prefer English, prefer non-auto-generated
            tracks.sort(key=lambda t: (
                0 if t.get('languageCode') == 'en' else 1,
                0 if t.get('kind') != 'asr' else 1
            ))
            
            # Step 4: Fetch transcript from best track
            transcript = self._fetch_transcript(tracks[0]['baseUrl'])
            
            if not transcript:
                result['error'] = 'Transcript is empty'
                return result
            
            result['transcript'] = transcript
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def extract_batch(self, video_ids):
        """Extract transcripts for multiple videos."""
        return [self.extract(vid) for vid in video_ids]
