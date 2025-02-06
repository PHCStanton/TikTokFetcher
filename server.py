from flask import Flask
from flask_cors import CORS
from routes import static_pages, auth_routes
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

@app.route('/')
def index():
    return 'TikTok Video Downloader API Server'

if __name__ == '__main__':
    # Use PORT environment variable for Replit deployment
    port = int(os.environ.get('PORT', 3000))
    # Production settings
    app.config['SERVER_NAME'] = os.getenv('TIKTOK_BASE_DOMAIN', 'api.tiktokrescue.online')
    app.run(host='0.0.0.0', port=port, ssl_context='adhoc')