from flask import Blueprint, request, redirect, render_template_string, jsonify, url_for, session
import os
from rich.console import Console

static_pages = Blueprint('static_pages', __name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')
console = Console()

@auth_routes.route('/tiktok/callback')
def tiktok_callback():
    """Handle TikTok OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    error_description = request.args.get('error_description')

    # Log the callback parameters for debugging
    console.print(f"[blue]Received callback - Code: {code}, State: {state}[/blue]")

    if error:
        console.print(f"[red]Auth Error: {error} - {error_description}[/red]")
        return render_template_string("""
            <h1>Authentication Error</h1>
            <p style="color: red;">{{ error }}: {{ description }}</p>
            <a href="/" style="
                display: inline-block;
                background-color: #00f2ea;
                color: black;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            ">Return to Home</a>
        """, error=error, description=error_description), 400

    if not code:
        return render_template_string("""
            <h1>Authentication Error</h1>
            <p style="color: red;">No authorization code provided. Please try again.</p>
            <a href="/" style="
                display: inline-block;
                background-color: #00f2ea;
                color: black;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            ">Return to Home</a>
        """), 400

    # Return the code in a user-friendly format
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Successful</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                    background-color: #f8f9fa;
                }
                .code-box {
                    background-color: #ffffff;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    font-family: monospace;
                    word-break: break-all;
                    border: 1px solid #dee2e6;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }
                .return-button {
                    display: inline-block;
                    background-color: #00f2ea;
                    color: black;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                    font-weight: bold;
                    transition: background-color 0.2s;
                }
                .return-button:hover {
                    background-color: #00d8d1;
                }
                .success-icon {
                    color: #28a745;
                    font-size: 48px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <h1>Authorization Successful</h1>
            <div class="success-icon">✓</div>
            <p>Your authorization code is:</p>
            <div class="code-box">{{ code }}</div>
            <p>Please copy this code and paste it back in the application.</p>
            <a href="/" class="return-button">Return to Home</a>
            <script>
                // Automatically copy code to clipboard
                const codeBox = document.querySelector('.code-box');
                codeBox.addEventListener('click', () => {
                    const textArea = document.createElement('textarea');
                    textArea.value = codeBox.textContent;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    codeBox.style.backgroundColor = '#e8f5e9';
                    setTimeout(() => {
                        codeBox.style.backgroundColor = '#ffffff';
                    }, 200);
                });
            </script>
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