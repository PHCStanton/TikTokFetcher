from flask import Blueprint, request, redirect, render_template_string, jsonify, session, url_for
import os
import time
import asyncio
from auth import TikTokAuth
from rich.console import Console

console = Console()
static_pages = Blueprint('static_pages', __name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')

@auth_routes.route('/tiktok/callback')
def tiktok_callback():
    """Handle TikTok OAuth2 callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')

    console.print(f"[blue]Callback URL accessed[/blue]")
    console.print(f"[blue]Full URL: {request.url}[/blue]")
    console.print(f"[blue]Code received: {code[:10]}...[/blue]" if code else "[red]No code received[/red]")
    console.print(f"[blue]State: {state}[/blue]")

    if error:
        console.print(f"[red]OAuth error: {error} - {error_description}[/red]")
        return render_template_string("""
            <h1>Authentication Error</h1>
            <p>Error: {{ error }}</p>
            <p>Description: {{ error_description }}</p>
            <p><a href="/">Try Again</a></p>
        """, error=error, error_description=error_description)

    if not code:
        console.print("[red]No authorization code provided in callback[/red]")
        return render_template_string("""
            <h1>Authentication Error</h1>
            <p>No authorization code was provided. Please try again.</p>
            <p><a href="/">Return to Home</a></p>
        """)

    try:
        auth = TikTokAuth()
        console.print("[blue]Attempting to get access token...[/blue]")

        # Get access token
        token_data = asyncio.run(auth.get_access_token(code))

        if not token_data:
            console.print("[red]Failed to get access token - token_data is None[/red]")
            return render_template_string("""
                <h1>Authentication Failed</h1>
                <p>Could not get access token. Please try again.</p>
                <p><a href="/">Return to Home</a></p>
            """)

        if 'access_token' not in token_data:
            console.print("[red]Failed to get access token - no access_token in response[/red]")
            return render_template_string("""
                <h1>Authentication Failed</h1>
                <p>Invalid token response. Please try again.</p>
                <p><a href="/">Return to Home</a></p>
            """)

        # Store in session
        session['access_token'] = token_data['access_token']
        session['token_expiry'] = time.time() + token_data.get('expires_in', 3600)

        console.print("[green]Successfully obtained and stored access token[/green]")

        # Redirect to main page
        return redirect(url_for('index'))

    except Exception as e:
        console.print(f"[red]Authentication error: {str(e)}[/red]")
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