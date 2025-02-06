from flask import Flask, render_template_string
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
import os

app = Flask(__name__)
CORS(app, resources={
    r"/auth/*": {"origins": ["https://api.tiktokrescue.online", "https://tiktokrescue.online"]},
    r"/privacy": {"origins": "*"},
    r"/terms": {"origins": "*"}
})

# Register blueprints
app.register_blueprint(static_pages)
app.register_blueprint(auth_routes)

# Initialize TikTok Auth
auth = TikTokAuth()

@app.route('/')
def index():
    # Generate auth URL
    auth_url = auth.get_auth_url()
    return render_template_string("""
        <h1>TikTok Video Downloader</h1>
        <p>To use this service, please authenticate with TikTok:</p>
        <a href="{{ auth_url }}" style="
            display: inline-block;
            background-color: #00f2ea;
            color: black;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
        ">Login with TikTok</a>
    """, auth_url=auth_url)

if __name__ == '__main__':
    # Use PORT environment variable for Replit deployment
    port = int(os.environ.get('PORT', 3000))
    # Remove SERVER_NAME to allow access via Replit domain
    app.run(host='0.0.0.0', port=port)