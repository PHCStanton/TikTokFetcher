from flask import Blueprint, request, redirect, render_template_string, jsonify
import os

static_pages = Blueprint('static_pages', __name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')

PRIVACY_POLICY = """
<h1>Privacy Policy for FetchTok</h1>
<p>Last updated: February 06, 2025</p>

<p>This Privacy Policy describes how FetchTok ("we", "us", or "our") collects, uses, and discloses your information when you use our service at https://api.tiktokrescue.online (the "Service").</p>

<h2>Information We Collect</h2>
<p>We only collect information necessary to provide the TikTok video downloading service, including:</p>
<ul>
    <li>TikTok video URLs you submit</li>
    <li>Temporary authentication tokens for TikTok API access</li>
</ul>

<h2>Contact Us</h2>
<p>If you have any questions about this Privacy Policy, please contact us through the application interface.</p>
"""

TERMS_OF_SERVICE = """
<h1>Terms of Service for FetchTok</h1>
<p>Last updated: February 06, 2025</p>

<p>By using FetchTok at https://api.tiktokrescue.online, you agree to these terms:</p>

<h2>Service Usage</h2>
<ul>
    <li>You may only download videos you have rights to access</li>
    <li>You agree to comply with TikTok's terms of service</li>
    <li>You will not use the service for any illegal purposes</li>
</ul>

<h2>Disclaimer</h2>
<p>The service is provided "as is" without warranties of any kind.</p>
"""

@static_pages.route('/privacy')
def privacy_policy():
    return render_template_string(PRIVACY_POLICY)

@static_pages.route('/terms')
def terms_of_service():
    return render_template_string(TERMS_OF_SERVICE)

@auth_routes.route('/tiktok/callback')
def tiktok_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        return jsonify({'error': 'No authorization code provided'}), 400

    # Return the code in a user-friendly format
    return render_template_string("""
        <h1>Authorization Successful</h1>
        <p>Your authorization code is: <strong>{{ code }}</strong></p>
        <p>Please copy this code and paste it back in the application.</p>
    """, code=code)