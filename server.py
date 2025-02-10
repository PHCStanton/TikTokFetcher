from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
from downloader import TikTokDownloader #This import assumes a downloader.py file exists.
import os
from datetime import datetime, timedelta
import threading
from collections import deque
from queue import Queue
import time

app = Flask(__name__)

# Force production mode
is_development = False

# Set up CORS for production domain
base_domain = os.getenv('TIKTOK_BASE_DOMAIN', 'tiktokrescue.online')
allowed_origins = [
    f"https://{base_domain}",
    f"https://api.{base_domain}",
    f"https://www.{base_domain}"
]

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
                downloader = TikTokDownloader()
                download_status[video_url] = {'status': 'downloading', 'progress': 0}
                # Start download process
                # Update progress in download_status
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
        # Generate auth URL
        auth_url = auth.get_auth_url()
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
                </style>
                <script>
                    function updateProgress() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                const queueElement = document.getElementById('queue-status');
                                const progressElement = document.getElementById('current-progress');
                                if (data.queue_size > 0) {
                                    queueElement.textContent = `Queue: ${data.queue_size}/5 videos`;
                                    if (data.current_download) {
                                        progressElement.style.width = data.current_download.progress + '%';
                                    }
                                }
                            });
                    }
                    setInterval(updateProgress, 1000);
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>TikTok Video Downloader</h1>
                        <p>Download your favorite TikTok videos easily and securely</p>
                    </div>

                    <form class="download-form" action="/download" method="POST">
                        <input type="text" name="url" class="url-input" placeholder="Enter TikTok video URL" required>
                        <select name="order" class="order-select">
                            <option value="latest">Latest First</option>
                            <option value="oldest">Oldest First</option>
                            <option value="popular">Most Popular First</option>
                        </select>
                        <button type="submit" class="login-btn">Add to Queue</button>
                    </form>

                    <div class="queue-status">
                        <h3>Download Status</h3>
                        <div id="queue-status">Queue: 0/5 videos</div>
                        <div class="progress-container">
                            <div class="progress-bar">
                                <div id="current-progress" class="progress-fill"></div>
                            </div>
                        </div>
                    </div>

                    <div class="rate-limit-info">
                        Note: Limited to 5 videos per hour per user
                    </div>
                </div>
            </body>
            </html>
        """, auth_url=auth_url)
    except Exception as e:
        app.logger.error(f"Error rendering index page: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/status')
def get_status():
    return jsonify({
        'queue_size': download_queue.qsize(),
        'current_download': next(
            (status for status in download_status.values() if status['status'] == 'downloading'),
            None
        )
    })

@app.route('/download', methods=['POST'])
def queue_download():
    url = request.form.get('url')
    order = request.form.get('order', 'latest')
    user_id = request.remote_addr  # Simple user identification

    # Check rate limit
    current_time = datetime.now()
    if user_id in user_downloads:
        download_times = user_downloads[user_id]
        # Remove downloads older than 1 hour
        download_times = [t for t in download_times if current_time - t < timedelta(hours=1)]
        if len(download_times) >= 5:
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        user_downloads[user_id] = download_times
    else:
        user_downloads[user_id] = []

    # Add to queue if not full
    if download_queue.qsize() < 5:
        download_queue.put((user_id, url))
        user_downloads[user_id].append(current_time)
        return jsonify({'message': 'Video added to queue'})
    else:
        return jsonify({'error': 'Queue is full. Please try again later.'}), 429

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)