from flask import Flask, render_template_string, request, redirect, url_for
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
import os

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

@app.route('/')
def index():
    try:
        # Generate auth URL
        auth_url = auth.get_auth_url()
        # Get the host URL for debugging
        host_url = request.host_url
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>TikTok Video Downloader</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        text-align: center;
                        background-color: #f5f5f5;
                    }
                    .container {
                        background-color: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .debug-info {
                        margin-top: 20px;
                        padding: 10px;
                        background-color: #f0f0f0;
                        border-radius: 5px;
                        font-size: 0.8em;
                    }
                    .login-btn {
                        display: inline-block;
                        background-color: #00f2ea;
                        color: black;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin-top: 20px;
                        font-weight: bold;
                        transition: background-color 0.3s;
                    }
                    .login-btn:hover {
                        background-color: #00d8d2;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>TikTok Video Downloader</h1>
                    <p>To use this service, please authenticate with TikTok:</p>
                    <a href="{{ auth_url }}" class="login-btn">Login with TikTok</a>
                </div>
                <div class="debug-info">
                    <p>Debug Info:</p>
                    <p>Host URL: {{ host_url }}</p>
                    <p>Redirect URI: {{ redirect_uri }}</p>
                    <p>Environment: Production</p>
                    <p>API Version: v2</p>
                </div>
            </body>
            </html>
        """, auth_url=auth_url, host_url=host_url, redirect_uri=auth.redirect_uri)
    except Exception as e:
        app.logger.error(f"Error rendering index page: {str(e)}")
        return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)