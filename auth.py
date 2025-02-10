import os
from rich.console import Console
import aiohttp
from typing import Optional, Dict
from urllib.parse import urlencode, urlparse
import asyncio

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TIKTOK_REDIRECT_URI', 'https://api.tiktokrescue.online/auth/tiktok/callback')
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'
        self.retry_delay = 5  # Increased delay between retries
        self.max_retries = 2  # Reduced number of retries to avoid hitting rate limits

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        # Set up the correct endpoints
        if self.is_development:
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"
            self.redirect_uri = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co/auth/tiktok/callback"
        else:
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

        self.console = Console()

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL with updated parameters"""
        try:
            params = {
                'client_key': self.client_key,
                'redirect_uri': self.redirect_uri,
                'response_type': 'code',
                'scope': 'user.info.basic,video.list',
                'state': csrf_state if csrf_state is not None else 'default_state',
                'platform': 'web'
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

        remaining_retries = self.max_retries
        while remaining_retries > 0:
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
                        elif response.status == 429:  # Rate limit exceeded
                            error_text = await response.text()
                            self.console.print(f"[yellow]Rate limit exceeded. Please wait {self.retry_delay} seconds before trying again.[/yellow]")
                            if remaining_retries > 1:  # Only wait if we're going to retry
                                await asyncio.sleep(self.retry_delay)
                        else:
                            error_text = await response.text()
                            self.console.print(f"[red]Auth failed: {response.status} - {error_text}[/red]")

                        remaining_retries -= 1
                        if remaining_retries > 0:
                            self.console.print(f"[yellow]Retrying... {remaining_retries} attempts remaining[/yellow]")
                        else:
                            self.console.print("[red]Maximum number of attempts reached. Please try again later.[/red]")

                        return None

            except aiohttp.ClientError as e:
                self.console.print(f"[red]Network error during authentication: {str(e)}[/red]")
                remaining_retries -= 1
            except Exception as e:
                self.console.print(f"[red]Unexpected error during authentication: {str(e)}[/red]")
                remaining_retries -= 1

            if remaining_retries > 0:
                await asyncio.sleep(self.retry_delay)

        return None