import asyncio
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session, Response
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
from downloader import TikTokDownloader
import threading
from collections import deque
from queue import Queue
import time
from rich.console import Console

console = Console()
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Set domain for development/production
PRODUCTION_DOMAIN = os.getenv('TIKTOK_BASE_DOMAIN', 'tik-tok-fetcher-pieterstanton.replit.app')
is_development = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'

# Domain verification middleware
@app.before_request
def verify_domain():
    if request.path == '/.well-known/tiktok-domain-verification.txt':
        return Response('Hl2FLqA7XY2ryMlN8E6Fv8vtwqJCflZR', mimetype='text/plain')
    return None

# Set up CORS for all domains during development
allowed_origins = [f"https://{PRODUCTION_DOMAIN}"]
if is_development:
    allowed_origins.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        f"https://{os.getenv('REPL_SLUG', '')}.{os.getenv('REPL_OWNER', '')}.repl.co"
    ])

console.print(f"[blue]Allowed CORS origins: {allowed_origins}[/blue]")
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Register blueprints
app.register_blueprint(static_pages)
app.register_blueprint(auth_routes, url_prefix='/auth')

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
        # Check if we're in bypass mode
        bypass_mode = os.getenv('BYPASS_AUTH', 'false').lower() == 'true'

        if bypass_mode:
            # Get the deployment URL for verification
            repl_slug = os.getenv('REPL_SLUG', '')
            repl_owner = os.getenv('REPL_OWNER', '')
            deployment_url = f"https://{repl_slug}.{repl_owner}.repl.co"
            verification_callback = f"{deployment_url}/auth/tiktok/callback"

            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>TikTok Domain Verification</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {
                            font-family: system-ui, -apple-system, sans-serif;
                            max-width: 800px;
                            margin: 20px auto;
                            padding: 20px;
                            line-height: 1.6;
                        }
                        .container {
                            background: #f5f5f5;
                            padding: 20px;
                            border-radius: 8px;
                            margin-top: 20px;
                        }
                        code {
                            background: #e0e0e0;
                            padding: 2px 6px;
                            border-radius: 4px;
                        }
                        .step {
                            margin-bottom: 20px;
                        }
                    </style>
                </head>
                <body>
                    <h1>TikTok Domain Verification Setup</h1>

                    <div class="container">
                        <h2>Current Redirect URI</h2>
                        <code>{{ redirect_uri }}</code>
                        <p>Use this URL in your TikTok Developer Portal setup.</p>
                    </div>

                    <h2>Steps for Domain Verification:</h2>

                    <div class="step">
                        <h3>1. TikTok Developer Portal Setup</h3>
                        <ul>
                            <li>Go to the <a href="https://developers.tiktok.com/" target="_blank">TikTok Developer Portal</a></li>
                            <li>Add the above Redirect URI to your application settings</li>
                        </ul>
                    </div>

                    <div class="step">
                        <h3>2. Domain Configuration</h3>
                        <ul>
                            <li>Copy the TXT record provided by TikTok</li>
                            <li>Go to your domain provider's DNS settings</li>
                            <li>Add a new TXT record with the value from TikTok</li>
                            <li>Wait for DNS propagation (can take up to 48 hours)</li>
                        </ul>
                    </div>

                    <div class="step">
                        <h3>3. Complete Verification</h3>
                        <ul>
                            <li>Return to TikTok Developer Portal</li>
                            <li>Click "Verify Domain"</li>
                            <li>Once verified, set BYPASS_AUTH=false in your environment variables</li>
                            <li>Add your TikTok API credentials to the environment variables</li>
                        </ul>
                    </div>
                </body>
                </html>
            """, redirect_uri=auth.redirect_uri)

        # Regular auth flow 
        is_authenticated = bool(session.get('access_token'))
        auth_url = None if is_authenticated else auth.get_auth_url()

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
    port = int(os.environ.get('PORT', 3000))  # Changed default port to 3000
    # Use production configuration when deployed
    if os.getenv('REPLIT_DEPLOYMENT') == '1':
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)