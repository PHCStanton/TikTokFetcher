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
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'  # Default to development mode
        self.retry_delay = 5
        self.max_retries = 2

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        # Set up the correct endpoints based on development mode
        if self.is_development:
            self.console = Console()
            self.console.print("[yellow]Running in development mode[/yellow]")
            self.auth_base_url = "https://open-api-test.tiktok.com/platform/oauth/connect/"
            self.token_url = "https://open-api-test.tiktok.com/oauth/access_token/"
            # Use Replit's domain for development
            if os.getenv('REPL_SLUG') and os.getenv('REPL_OWNER'):
                self.redirect_uri = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co/auth/tiktok/callback"
        else:
            self.console = Console()
            self.console.print("[green]Running in production mode[/green]")
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

    def get_auth_url(self, csrf_state: Optional[str] = None) -> str:
        """Generate TikTok OAuth URL with proper scopes and parameters"""
        try:
            params = {
                'client_key': self.client_key,
                'redirect_uri': self.redirect_uri,
                'response_type': 'code',
                'scope': 'user.info.basic,video.list',
                'state': csrf_state if csrf_state is not None else 'default_state'
            }

            # Add platform parameter only in production mode
            if not self.is_development:
                params['platform'] = 'web'

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
                async with aiohttp.ClientSession() as session:
                    payload = {
                        'client_key': self.client_key,
                        'client_secret': self.client_secret,
                        'code': code,
                        'grant_type': 'authorization_code'
                    }

                    self.console.print(f"[blue]Attempting to get access token from {self.token_url}[/blue]")
                    async with session.post(self.token_url, data=payload) as response:
                        response_text = await response.text()
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and 'access_token' in data['data']:
                                self.console.print("[green]Successfully obtained access token[/green]")
                                return data['data']
                            self.console.print(f"[red]Invalid response format from TikTok API: {response_text}[/red]")
                        elif response.status == 429:
                            self.console.print(f"[yellow]Rate limit exceeded. Waiting {self.retry_delay} seconds...[/yellow]")
                            if remaining_retries > 1:
                                await asyncio.sleep(self.retry_delay)
                        else:
                            self.console.print(f"[red]Auth failed ({response.status}): {response_text}[/red]")

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