import os
from rich.console import Console
import aiohttp
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode, urlparse

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TIKTOK_REDIRECT_URI', 'https://api.tiktokrescue.online/auth/tiktok/callback')
        self.base_domain = os.getenv('TIKTOK_BASE_DOMAIN', 'tiktokrescue.online')
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'

        if not all([self.client_key, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, and TIKTOK_REDIRECT_URI")

        # Verify domain configuration
        redirect_domain = urlparse(self.redirect_uri).netloc
        if not redirect_domain.endswith(self.base_domain) and not self.is_development:
            raise ValueError(f"Redirect URI domain {redirect_domain} does not match base domain {self.base_domain}")

        # Use test endpoints in development mode
        if self.is_development:
            self.auth_base_url = "https://open-api-test.tiktok.com/platform/oauth/connect/"
            self.token_url = "https://open-api-test.tiktok.com/oauth/access_token/"
            if not self.redirect_uri or '.replit.app' in self.redirect_uri:
                self.redirect_uri = "https://fetchtok.replit.dev/callback"  # Development callback URL
        else:
            self.auth_base_url = "https://open-api.tiktok.com/platform/oauth/connect/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

        self.console = Console()

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL with proper domain verification"""
        try:
            params = {
                'client_key': self.client_key,
                'redirect_uri': self.redirect_uri,
                'response_type': 'code',
                'scope': 'user.info.basic,video.list',
                'state': csrf_state if csrf_state is not None else 'default_state'
            }
            return f"{self.auth_base_url}?{urlencode(params)}"
        except Exception as e:
            self.console.print(f"[red]Error generating auth URL: {str(e)}[/red]")
            raise

    async def get_access_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token with improved error handling"""
        if not code:
            self.console.print("[red]Authorization code is required[/red]")
            return None

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'client_key': self.client_key,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code'
                }

                async with session.post(self.token_url, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'data' in data and 'access_token' in data['data']:
                            return data['data']
                        self.console.print("[red]Invalid response format from TikTok API[/red]")
                    else:
                        error_text = await response.text()
                        self.console.print(f"[red]Auth failed: {response.status} - {error_text}[/red]")
                    return None

        except aiohttp.ClientError as e:
            self.console.print(f"[red]Network error during authentication: {str(e)}[/red]")
            return None
        except Exception as e:
            self.console.print(f"[red]Unexpected error during authentication: {str(e)}[/red]")
            return None