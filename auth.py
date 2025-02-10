import os
from rich.console import Console
import aiohttp
import time
import asyncio
from typing import Optional, Dict
from urllib.parse import urlencode, urlparse

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.is_development = True  # Force development mode for Replit
        self.is_sandbox = False  # Disable sandbox mode since endpoints are not accessible
        self.retry_count = 0
        self.max_retries = 3
        self.base_delay = 2  # Base delay in seconds

        # Set up the correct endpoints based on environment
        if self.is_development:
            repl_slug = os.getenv('REPL_SLUG', '')
            repl_owner = os.getenv('REPL_OWNER', '')
            self.redirect_uri = f"https://{repl_slug}.{repl_owner}.repl.dev/callback"
            self.auth_base_url = "https://www.tiktok.com/v2/auth/authorize/"
            self.token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        else:
            base_domain = os.getenv('TIKTOK_BASE_DOMAIN', 'tiktokrescue.online')
            self.redirect_uri = f"https://api.{base_domain}/auth/tiktok/callback"
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        self.console = Console()

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL with updated parameters"""
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

    async def _exponential_backoff(self):
        """Implement exponential backoff for rate limits"""
        if self.retry_count >= self.max_retries:
            raise Exception("Maximum retry attempts reached. Please try again later.")

        delay = self.base_delay * (2 ** self.retry_count)
        self.console.print(f"[yellow]Rate limit reached. Waiting {delay} seconds before retry...[/yellow]")
        await asyncio.sleep(delay)
        self.retry_count += 1

    async def get_access_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token with retry logic"""
        if not code:
            self.console.print("[red]Authorization code is required[/red]")
            return None

        while self.retry_count < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        'client_key': self.client_key,
                        'client_secret': self.client_secret,
                        'code': code,
                        'grant_type': 'authorization_code',
                        'redirect_uri': self.redirect_uri  # Include redirect_uri in token request
                    }

                    async with session.post(self.token_url, data=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and 'access_token' in data['data']:
                                self.retry_count = 0  # Reset retry count on success
                                return data['data']
                            self.console.print("[red]Invalid response format from TikTok API[/red]")
                        elif response.status == 429:  # Rate limit
                            await self._exponential_backoff()
                            continue
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

        self.console.print("[red]Maximum retry attempts reached. Please try again later.[/red]")
        return None