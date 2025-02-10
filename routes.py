from flask import Blueprint, request, redirect, render_template_string, jsonify, session, url_for
import os
import time
import asyncio
from auth import TikTokAuth

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
            <p><a href="/">Try Again</a></p>
        """, error=error, error_description=error_description)

    if not code:
        return jsonify({'error': 'No authorization code provided'}), 400

    try:
        auth = TikTokAuth()
        # Get access token
        token_data = asyncio.run(auth.get_access_token(code))

        if not token_data or 'access_token' not in token_data:
            return render_template_string("""
                <h1>Authentication Failed</h1>
                <p>Could not get access token. Please try again.</p>
                <p><a href="/">Return to Home</a></p>
            """)

        # Store in session
        session['access_token'] = token_data['access_token']
        session['token_expiry'] = time.time() + token_data.get('expires_in', 3600)

        # Redirect to main page
        return redirect(url_for('index'))

    except Exception as e:
        return render_template_string("""
            <h1>Authentication Error</h1>
            <p>An error occurred during authentication: {{ error }}</p>
            <p><a href="/">Try Again</a></p>
        """, error=str(e))

@static_pages.route('/privacy')
def privacy():
    return render_template_string("""
        <h1>Privacy Policy</h1>
        <p>Your privacy is important to us...</p>
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