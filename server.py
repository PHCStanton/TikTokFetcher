from flask import Flask, render_template_string, request, redirect, url_for
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
import os

app = Flask(__name__)

# Force development mode for Replit
is_development = True

# Set up CORS for Replit domain
repl_slug = os.getenv('REPL_SLUG', '')
repl_owner = os.getenv('REPL_OWNER', '')
allowed_origins = [f"https://{repl_slug}.{repl_owner}.repl.dev"]

CORS(app, resources={
    r"/callback": {"origins": allowed_origins},
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
                }
            </style>
        </head>
        <body>
            <h1>TikTok Video Downloader</h1>
            <p>To use this service, please authenticate with TikTok:</p>
            <a href="{{ auth_url }}" class="login-btn">Login with TikTok</a>
            <div class="debug-info">
                <p>Debug Info:</p>
                <p>Host URL: {{ host_url }}</p>
                <p>Redirect URI: {{ redirect_uri }}</p>
                <p>Development Mode: Enabled</p>
            </div>
        </body>
        </html>
    """, auth_url=auth_url, host_url=host_url, redirect_uri=auth.redirect_uri)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if code:
        return f"""
        <html>
        <body>
            <h1>Authorization Code Received</h1>
            <p>Your authorization code is: <strong>{code}</strong></p>
            <p>Please copy this code and paste it back in the command line interface.</p>
        </body>
        </html>
        """
    return "No authorization code received", 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)