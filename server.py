from flask import Flask, render_template_string
from flask_cors import CORS
from routes import static_pages, auth_routes
from auth import TikTokAuth
import os
from rich.console import Console

console = Console()

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
        <!DOCTYPE html>
        <html>
        <head>
            <title>TikTok Video Downloader</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                }
                .login-button {
                    display: inline-block;
                    background-color: #00f2ea;
                    color: black;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                    font-weight: bold;
                }
                .login-button:hover {
                    background-color: #00d8d1;
                }
            </style>
        </head>
        <body>
            <h1>TikTok Video Downloader</h1>
            <p>To use this service, please authenticate with TikTok:</p>
            <a href="{{ auth_url }}" class="login-button">Login with TikTok</a>
        </body>
        </html>
    """, auth_url=auth_url)

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 3000))
        console.print(f"[green]Starting server on port {port}...[/green]")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        console.print(f"[red]Failed to start server: {str(e)}[/red]")