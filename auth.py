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
        self.is_development = True  # Force development mode
        self.is_sandbox = True  # Enable sandbox mode
        self.retry_count = 0
        self.max_retries = 3
        self.base_delay = 2
        self._access_token = None
        self._token_expiry = None

        # Set up sandbox endpoints
        repl_id = os.getenv('REPL_ID', '')
        repl_slug = os.getenv('REPL_SLUG', '')
        self.redirect_uri = f"https://{repl_slug}.{repl_id}.repl.co/auth/tiktok/callback"
        self.auth_base_url = "https://www.tiktok.com/v2/auth/authorize/"
        self.token_url = "https://open-api.tiktok.com/oauth/access_token/"
        else:
            base_domain = os.environ['TIKTOK_BASE_DOMAIN']
            self.redirect_uri = f"https://{base_domain}/auth/tiktok/callback"
            self.auth_base_url = "https://www.tiktok.com/v2/auth/authorize/"
            self.token_url = "https://open.tiktokapis.com/v2/oauth/token/"

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        self.console = Console()

    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token if it exists and is valid"""
        if self._access_token and self._token_expiry and time.time() < self._token_expiry:
            return self._access_token
        return None

    def is_authenticated(self) -> bool:
        """Check if the user is currently authenticated with a valid token"""
        return bool(self.access_token)

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

            auth_url = f"{self.auth_base_url}?{urlencode(params)}"
            self.console.print(f"[green]Generated auth URL for development mode: {auth_url}[/green]")
            return auth_url
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
                        'redirect_uri': self.redirect_uri
                    }

                    self.console.print(f"[green]Attempting to get access token in development mode[/green]")
                    self.console.print(f"[blue]Using token URL: {self.token_url}[/blue]")

                    async with session.post(self.token_url, data=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and 'access_token' in data['data']:
                                token_data = data['data']
                                self._access_token = token_data['access_token']
                                # Set token expiry (usually expires_in is in seconds)
                                self._token_expiry = time.time() + token_data.get('expires_in', 3600)
                                self.retry_count = 0  # Reset retry count on success
                                return token_data
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