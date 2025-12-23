from flask import Flask, render_template, jsonify, request
from youtube_api import YouTubeChannel
from transcriber import TranscriptExtractor
import config
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

yt = YouTubeChannel(config.YOUTUBE_API_KEY)
transcriber = TranscriptExtractor()

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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
