import os
from rich.console import Console
import aiohttp
from typing import Optional, Dict
from urllib.parse import urlencode, urlparse

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TIKTOK_REDIRECT_URI', 'https://api.tiktokrescue.online/auth/tiktok/callback')
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        # Use test endpoints in development mode
        if self.is_development:
            self.auth_base_url = "https://open-api-test.tiktok.com/platform/oauth/connect/"
            self.token_url = "https://open-api-test.tiktok.com/oauth/access_token/"
            self.redirect_uri = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co/auth/tiktok/callback"
        else:
            self.auth_base_url = "https://open-api.tiktok.com/platform/oauth/connect/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

        self.console = Console()

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL"""
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
        """Exchange authorization code for access token"""
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