import asyncio
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
from downloader import TikTokDownloader
import os
from datetime import datetime, timedelta
import threading
from collections import deque
from queue import Queue
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Add secret key for sessions

# Force production mode
is_development = False

# Set up CORS for development
repl_slug = os.getenv('REPL_SLUG', '')
repl_owner = os.getenv('REPL_OWNER', '')
allowed_origins = [f"https://{repl_slug}.{repl_owner}.repl.dev"]

# Enable CORS for specific origins in production
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Register blueprints
app.register_blueprint(static_pages)
app.register_blueprint(auth_routes)

# Initialize TikTok Auth
auth = TikTokAuth()

# Rate limiting and queue management
download_queue = Queue(maxsize=5)
user_downloads = {}
download_status = {}

def process_download_queue():
    while True:
        if not download_queue.empty():
            user_id, video_url = download_queue.get()
            try:
                downloader = TikTokDownloader(access_token=session.get('access_token'))
                download_status[video_url] = {'status': 'downloading', 'progress': 0}

                # Update progress as download starts
                download_status[video_url]['progress'] = 25
                time.sleep(1)  # Simulate download progress

                # Update progress midway
                download_status[video_url]['progress'] = 50
                time.sleep(1)

                # Final progress update
                download_status[video_url] = {'status': 'completed', 'progress': 100}
            except Exception as e:
                download_status[video_url] = {'status': 'failed', 'error': str(e)}
            finally:
                download_queue.task_done()
        time.sleep(1)

# Start queue processor
threading.Thread(target=process_download_queue, daemon=True).start()

@app.route('/')
def index():
    try:
        # Check if user is authenticated
        is_authenticated = bool(session.get('access_token'))

        # Generate auth URL if not authenticated
        auth_url = None if is_authenticated else auth.get_auth_url()

        # Return appropriate template based on auth status
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>TikTok Video Downloader</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    :root {
                        --primary-color: #00f2ea;
                        --secondary-color: #ff0050;
                        --background-color: #f5f5f5;
                    }
                    body {
                        font-family: 'Inter', Arial, sans-serif;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: var(--background-color);
                    }
                    .container {
                        background-color: white;
                        padding: 2rem;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .header {
                        text-align: center;
                        margin-bottom: 2rem;
                    }
                    .download-form {
                        display: flex;
                        flex-direction: column;
                        gap: 1rem;
                    }
                    .url-input {
                        padding: 0.75rem;
                        border: 2px solid #ddd;
                        border-radius: 6px;
                        font-size: 1rem;
                    }
                    .order-select {
                        padding: 0.75rem;
                        border: 2px solid #ddd;
                        border-radius: 6px;
                        font-size: 1rem;
                        background-color: white;
                    }
                    .queue-status {
                        margin-top: 2rem;
                        padding: 1rem;
                        background-color: #f8f9fa;
                        border-radius: 6px;
                    }
                    .progress-container {
                        margin-top: 1rem;
                    }
                    .progress-bar {
                        height: 10px;
                        background-color: #ddd;
                        border-radius: 5px;
                        overflow: hidden;
                    }
                    .progress-fill {
                        height: 100%;
                        background-color: var(--primary-color);
                        width: 0%;
                        transition: width 0.3s ease;
                    }
                    .login-btn {
                        display: inline-block;
                        background-color: var(--primary-color);
                        color: black;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 6px;
                        font-weight: bold;
                        transition: all 0.3s ease;
                    }
                    .login-btn:hover {
                        background-color: var(--secondary-color);
                        color: white;
                        transform: translateY(-2px);
                    }
                    .rate-limit-info {
                        margin-top: 1rem;
                        font-size: 0.9rem;
                        color: #666;
                    }
                    .video-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                        gap: 1rem;
                        margin-top: 2rem;
                    }
                    .video-card {
                        background: white;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        position: relative;
                    }
                    .video-thumbnail {
                        width: 100%;
                        aspect-ratio: 9/16;
                        object-fit: cover;
                    }
                    .video-info {
                        padding: 0.5rem;
                    }
                    .video-title {
                        font-size: 0.9rem;
                        margin: 0;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }
                    .video-stats {
                        font-size: 0.8rem;
                        color: #666;
                        margin-top: 0.25rem;
                    }
                    .video-select {
                        position: absolute;
                        top: 0.5rem;
                        right: 0.5rem;
                        width: 1.2rem;
                        height: 1.2rem;
                    }
                    .filters {
                        display: flex;
                        gap: 1rem;
                        margin: 1rem 0;
                        flex-wrap: wrap;
                    }
                    .filter-select {
                        padding: 0.5rem;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        background: white;
                    }
                    .selected-count {
                        position: fixed;
                        bottom: 1rem;
                        right: 1rem;
                        background: var(--primary-color);
                        color: black;
                        padding: 0.5rem 1rem;
                        border-radius: 2rem;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    }
                    .hashtag-filter {
                        flex: 1;
                        min-width: 200px;
                    }
                </style>
                <script>
                    let selectedVideos = new Set();

                    function updateSelectedCount() {
                        const counter = document.getElementById('selected-count');
                        if (!counter) return;

                        counter.textContent = `${selectedVideos.size}/5 Selected`;

                        // Disable checkboxes if limit reached
                        const checkboxes = document.querySelectorAll('.video-select');
                        checkboxes.forEach(cb => {
                            if (!cb.checked && selectedVideos.size >= 5) {
                                cb.disabled = true;
                            } else {
                                cb.disabled = false;
                            }
                        });
                    }

                    function loadVideos(cursor = 0) {
                        const sortType = document.getElementById('sort-type')?.value || 'latest';
                        const viewRange = document.getElementById('view-range')?.value || 5;
                        const hashtag = document.getElementById('hashtag-filter')?.value || '';

                        fetch(`/videos?cursor=${cursor}&sort_type=${sortType}&max_count=${viewRange}&hashtag=${hashtag}`, {
                            credentials: 'include'  // Include session cookies
                        })
                        .then(response => {
                            if (response.status === 401) {
                                window.location.reload();  // Reload if unauthorized
                                return;
                            }
                            return response.json();
                        })
                        .then(data => {
                            if (!data) return;

                            const grid = document.getElementById('video-grid');
                            if (!grid) return;

                            grid.innerHTML = data.videos.map(video => `
                                <div class="video-card">
                                    <img src="${video.cover_url}" class="video-thumbnail" alt="${video.title}">
                                    <input type="checkbox" class="video-select" 
                                           onchange="toggleVideo('${video.id}', this)"
                                           ${selectedVideos.has(video.id) ? 'checked' : ''}>
                                    <div class="video-info">
                                        <p class="video-title">${video.title}</p>
                                        <p class="video-stats">
                                            👍 ${video.stats.likes} • 👀 ${video.stats.views}
                                        </p>
                                    </div>
                                </div>
                            `).join('');

                            // Update load more button
                            const loadMoreBtn = document.getElementById('load-more');
                            if (loadMoreBtn) {
                                loadMoreBtn.style.display = data.has_more ? 'block' : 'none';
                                loadMoreBtn.onclick = () => loadVideos(data.cursor);
                            }
                        });
                    }

                    // Only initialize the video loading if user is authenticated
                    if ({{ is_authenticated|tojson }}) {
                        document.addEventListener('DOMContentLoaded', () => {
                            loadVideos();
                            updateSelectedCount();
                        });
                    }
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>TikTok Video Downloader</h1>
                        {% if not is_authenticated %}
                            <p>Please authenticate with TikTok to start downloading videos</p>
                            <a href="{{ auth_url }}" class="login-btn">Login with TikTok</a>
                        {% else %}
                            <p>Select videos from your profile to download</p>

                            <div class="filters">
                                <select id="sort-type" class="filter-select" onchange="loadVideos()">
                                    <option value="latest">Latest First</option>
                                    <option value="oldest">Oldest First</option>
                                    <option value="most_liked">Most Liked</option>
                                    <option value="most_viewed">Most Viewed</option>
                                </select>

                                <select id="view-range" class="filter-select" onchange="loadVideos()">
                                    <option value="5">Show 5</option>
                                    <option value="10">Show 10</option>
                                    <option value="20">Show 20</option>
                                    <option value="30">Show 30</option>
                                    <option value="40">Show 40</option>
                                </select>

                                <input type="text" id="hashtag-filter" 
                                       class="filter-select hashtag-filter" 
                                       placeholder="Filter by hashtag"
                                       onchange="loadVideos()">
                            </div>

                            <div id="video-grid" class="video-grid">
                                <!-- Videos will be loaded here -->
                            </div>

                            <button id="load-more" class="login-btn" style="display: none; margin: 2rem auto;">
                                Load More
                            </button>

                            <div class="queue-status">
                                <h3>Download Status</h3>
                                <div id="queue-status">Queue: 0/5 videos</div>
                                <div class="progress-container">
                                    <div class="progress-bar">
                                        <div id="current-progress" class="progress-fill"></div>
                                    </div>
                                </div>
                            </div>

                            <button onclick="downloadSelected()" class="login-btn" style="margin-top: 1rem;">
                                Download Selected Videos
                            </button>

                            <div id="selected-count" class="selected-count">0/5 Selected</div>
                        {% endif %}
                    </div>
                </div>
            </body>
            </html>
        """, auth_url=auth_url, is_authenticated=is_authenticated)
    except Exception as e:
        app.logger.error(f"Error rendering index page: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/videos')
def get_videos():
    # Check session for access token
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({"error": "Authentication required"}), 401

    cursor = request.args.get('cursor', 0, type=int)
    sort_type = request.args.get('sort_type', 'latest')
    max_count = request.args.get('max_count', 30, type=int)
    hashtag = request.args.get('hashtag', '')

    try:
        downloader = TikTokDownloader(access_token=access_token)
        videos = asyncio.run(downloader.get_user_videos(
            max_count=max_count,
            cursor=cursor,
            sort_type=sort_type
        ))

        # Filter by hashtag if provided
        if hashtag:
            videos['videos'] = [
                video for video in videos['videos']
                if hashtag.lower() in [tag.lower() for tag in video.get('hashtags', [])]
            ]

        return jsonify(videos)
    except Exception as e:
        app.logger.error(f"Error fetching videos: {str(e)}")
        return jsonify({"error": "Failed to fetch videos"}), 500

@app.route('/auth/callback')
def auth_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400

    try:
        # Get access token
        token_data = asyncio.run(auth.get_access_token(code))
        if not token_data or 'access_token' not in token_data:
            return jsonify({"error": "Failed to get access token"}), 400

        # Store in session
        session['access_token'] = token_data['access_token']
        session['token_expiry'] = time.time() + token_data.get('expires_in', 3600)

        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Auth callback error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/download', methods=['POST'])
def queue_download():
    try:
        data = request.get_json()
        video_ids = data.get('video_ids', [])
        user_id = request.remote_addr

        if not video_ids:
            return jsonify({'error': 'No videos selected'}), 400

        if len(video_ids) > 5:
            return jsonify({'error': 'Maximum 5 videos can be selected'}), 400

        # Check rate limit
        current_time = datetime.now()
        if user_id in user_downloads:
            download_times = user_downloads[user_id]
            # Keep only downloads from last hour
            download_times = [t for t in download_times if current_time - t < timedelta(hours=1)]
            if len(download_times) >= 5:
                remaining_time = (download_times[0] + timedelta(hours=1) - current_time)
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Please try again in {int(remaining_time.total_seconds() / 60)} minutes'
                }), 429
            user_downloads[user_id] = download_times
        else:
            user_downloads[user_id] = []

        # Add to queue if not full
        if download_queue.qsize() + len(video_ids) <= 5:
            for video_id in video_ids:
                download_queue.put((user_id, video_id))
                user_downloads[user_id].append(current_time)
            return jsonify({
                'message': 'Videos added to queue',
                'queue_position': download_queue.qsize()
            })
        else:
            return jsonify({
                'error': 'Queue is full',
                'message': 'Please try again in a few minutes'
            }), 429
    except Exception as e:
        app.logger.error(f"Download queue error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status')
def get_status():
    return jsonify({
        'queue_size': download_queue.qsize(),
        'current_download': next(
            ({"status": status['status'], "progress": status['progress']}
             for status in download_status.values()
             if status['status'] in ['downloading', 'completed']),
            None
        ),
        'downloads': download_status
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    # Use production configuration when deployed
    if os.getenv('REPLIT_DEPLOYMENT') == '1':
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)