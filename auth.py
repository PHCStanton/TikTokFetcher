import os
from rich.console import Console
import aiohttp
from typing import Optional, Dict
from urllib.parse import urlencode

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TIKTOK_REDIRECT_URI')
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'
        if self.is_development:
            self.auth_base_url = "https://open-api-test.tiktok.com/platform/oauth/connect/"
            self.token_url = "https://open-api-test.tiktok.com/oauth/access_token/"
        self.console = Console()
        self.auth_base_url = "https://open-api.tiktok.com/platform/oauth/connect/"
        self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL"""
        params = {
            'client_key': self.client_key,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'user.info.basic,video.list',
            'state': csrf_state if csrf_state is not None else 'default_state'
        }
        return f"{self.auth_base_url}?{urlencode(params)}"

    async def get_access_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        if not all([self.client_key, self.client_secret, code]):
            self.console.print("[red]Missing required authentication parameters[/red]")
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
                        return await response.json()
                    self.console.print(f"[red]Auth failed: {response.status}[/red]")
                    return None

        except Exception as e:
            self.console.print(f"[red]Auth error: {str(e)}[/red]")
            return None