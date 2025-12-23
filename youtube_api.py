import googleapiclient.discovery
import googleapiclient.errors

class YouTubeChannel:
    def __init__(self, api_key):
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=api_key
        )
        self.channel_id = None

    def resolve_handle(self, handle):
        """Resolves a channel handle (e.g., @RafTalks) to a channel ID."""
        if not handle.startswith('@'):
            handle = '@' + handle
        
        try:
            request = self.youtube.channels().list(
                part="id,snippet",
                forHandle=handle
            )
            response = request.execute()
            
            if response.get('items'):
                self.channel_id = response['items'][0]['id']
                return self.channel_id
            else:
                # Fallback to search if handle resolution fails
                request = self.youtube.search().list(
                    part="snippet",
                    q=handle,
                    type="channel",
                    maxResults=1
                )
                response = request.execute()
                if response.get('items'):
                    self.channel_id = response['items'][0]['id']['channelId']
                    return self.channel_id
                    
        except googleapiclient.errors.HttpError as e:
            print(f"An error occurred: {e}")
        
        return None

    def get_channel_videos(self, channel_id, max_results=50, page_token=None):
        """Fetches videos from a specific channel."""
        try:
            # First, get the 'uploads' playlist ID for the channel
            request = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return [], None
                
            uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Now, list videos in that playlist
            request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_results,
                pageToken=page_token
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                videos.append({
                    'video_id': item['contentDetails']['videoId'],
                    'title': item['snippet']['title'],
                    'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                    'published_at': item['snippet']['publishedAt']
                })
            
            return videos, response.get('nextPageToken')
            
        except googleapiclient.errors.HttpError as e:
            print(f"An error occurred: {e}")
            return [], None

    def search_channel(self, channel_id, query, max_results=50, page_token=None):
        """Searches for videos within a specific channel."""
        try:
            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                q=query,
                type="video",
                maxResults=max_results,
                pageToken=page_token,
                order="date"
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                    'published_at': item['snippet']['publishedAt']
                })
            
            return videos, response.get('nextPageToken')
            
        except googleapiclient.errors.HttpError as e:
            print(f"An error occurred: {e}")
            return [], None

    def get_video_details(self, video_ids):
        """Gets detailed information (e.g., duration) for a list of videos."""
        if not video_ids:
            return []
            
        try:
            request = self.youtube.videos().list(
                part="snippet,contentDetails",
                id=",".join(video_ids)
            )
            response = request.execute()
            
            details = []
            for item in response.get('items', []):
                details.append({
                    'video_id': item['id'],
                    'title': item['snippet']['title'],
                    'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                    'published_at': item['snippet']['publishedAt'],
                    'duration': item['contentDetails']['duration']
                })
            return details
        except googleapiclient.errors.HttpError as e:
            print(f"An error occurred: {e}")
            return []
