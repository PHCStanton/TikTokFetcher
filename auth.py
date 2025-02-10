import os
from rich.console import Console
import aiohttp
from typing import Optional, Dict
from urllib.parse import urlencode
import asyncio
import json
import time

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TIKTOK_REDIRECT_URI', 'https://api.tiktokrescue.online/auth/tiktok/callback')
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'
        self.base_retry_delay = 3  # Start with 3 seconds
        self.max_retries = 5
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        # Updated endpoints for 2025
        if self.is_development:
            self.console = Console()
            self.console.print("[yellow]Running in development mode[/yellow]")
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"  # Use main API endpoint
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"
            if os.getenv('REPL_SLUG') and os.getenv('REPL_OWNER'):
                self.redirect_uri = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co/auth/tiktok/callback"
        else:
            self.console = Console()
            self.console.print("[green]Running in production mode[/green]")
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

    async def _rate_limit(self):
        """Ensure minimum time between requests"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL with proper scopes and parameters"""
        try:
            # Simplified scopes based on 2025 TikTok API requirements
            params = {
                'client_key': self.client_key,
                'redirect_uri': self.redirect_uri,
                'response_type': 'code',
                'scope': 'user.info.basic,video.list',  # Simplified scopes
                'state': csrf_state if csrf_state is not None else 'default_state'
            }

            auth_url = f"{self.auth_base_url}?{urlencode(params)}"
            self.console.print(f"[blue]Generated auth URL: {auth_url}[/blue]")
            return auth_url
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
                # Respect rate limiting
                await self._rate_limit()

                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    payload = {
                        'client_key': self.client_key,
                        'client_secret': self.client_secret,
                        'code': code,
                        'grant_type': 'authorization_code'
                    }

                    self.console.print(f"[blue]Attempting to get access token (attempt {self.max_retries - remaining_retries + 1}/{self.max_retries})[/blue]")

                    async with session.post(self.token_url, data=payload) as response:
                        response_text = await response.text()

                        if response.status == 200:
                            try:
                                data = json.loads(response_text)
                                if data.get('message') == 'success' and 'data' in data:
                                    self.console.print("[green]Successfully obtained access token[/green]")
                                    return data['data']
                                else:
                                    self.console.print(f"[yellow]Invalid response format: {response_text}[/yellow]")
                            except json.JSONDecodeError:
                                self.console.print("[red]Invalid JSON response from TikTok API[/red]")

                        elif response.status == 429:
                            self.console.print("[yellow]Rate limit reached. Waiting before retry...[/yellow]")
                        else:
                            self.console.print(f"[red]Auth failed (Status {response.status})[/red]")

            except aiohttp.ClientError as e:
                self.console.print(f"[red]Network error: {str(e)}[/red]")
            except asyncio.TimeoutError:
                self.console.print("[red]Request timed out[/red]")
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {str(e)}[/red]")

            remaining_retries -= 1
            if remaining_retries > 0:
                # Exponential backoff
                delay = self.base_retry_delay * (2 ** (self.max_retries - remaining_retries))
                self.console.print(f"[yellow]Waiting {delay} seconds before retry... ({remaining_retries} attempts remaining)[/yellow]")
                await asyncio.sleep(delay)
            else:
                self.console.print("[red]All retry attempts exhausted. Please try again later.[/red]")

        return None