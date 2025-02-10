from flask import Blueprint, request, redirect, render_template_string, jsonify
import os

static_pages = Blueprint('static_pages', __name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')

@auth_routes.route('/tiktok/callback')
def tiktok_callback():
    """Handle TikTok OAuth2 callback with V2 API support"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')

    if error:
        return render_template_string("""
            <h1>Authentication Error</h1>
            <p>Error: {{ error }}</p>
            <p>Description: {{ error_description }}</p>
        """, error=error, error_description=error_description)

    if not code:
        return jsonify({'error': 'No authorization code provided'}), 400

    # Return the code in a user-friendly format
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Successful</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 20px auto;
                    padding: 20px;
                    text-align: center;
                }
                .code-box {
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    word-break: break-all;
                }
            </style>
        </head>
        <body>
            <h1>Authorization Successful</h1>
            <p>Your authorization code is:</p>
            <div class="code-box">
                <strong>{{ code }}</strong>
            </div>
            <p>Please copy this code and paste it back in the application.</p>
        </body>
        </html>
    """, code=code)

@static_pages.route('/privacy')
def privacy_policy():
    return render_template_string("""
        <h1>Privacy Policy for FetchTok</h1>
        <p>Last updated: February 10, 2025</p>

        <p>This Privacy Policy describes how FetchTok ("we", "us", or "our") collects, uses, and discloses your information when you use our service.</p>

        <h2>Information We Collect</h2>
        <p>We only collect information necessary to provide the TikTok video downloading service, including:</p>
        <ul>
            <li>TikTok video URLs you submit</li>
            <li>Temporary authentication tokens for TikTok API access</li>
        </ul>

        <h2>Contact Us</h2>
        <p>If you have any questions about this Privacy Policy, please contact us through the application interface.</p>
    """)

@static_pages.route('/terms')
def terms_of_service():
    return render_template_string("""
        <h1>Terms of Service for FetchTok</h1>
        <p>Last updated: February 10, 2025</p>

        <p>By using our service, you agree to these terms:</p>

        <h2>Service Usage</h2>
        <ul>
            <li>You may only download videos you have rights to access</li>
            <li>You agree to comply with TikTok's terms of service</li>
            <li>You will not use the service for any illegal purposes</li>
        </ul>

        <h2>Disclaimer</h2>
        <p>The service is provided "as is" without warranties of any kind.</p>
    """)