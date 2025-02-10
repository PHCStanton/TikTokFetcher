import os
from rich.console import Console
import aiohttp
from typing import Optional, Dict
from urllib.parse import urlencode, urlparse
import asyncio
import socket

class TikTokAuth:
    def __init__(self):
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TIKTOK_REDIRECT_URI', 'https://api.tiktokrescue.online/auth/tiktok/callback')
        self.is_development = os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'true'
        self.retry_delay = 5
        self.max_retries = 3
        self.timeout = aiohttp.ClientTimeout(total=30)

        if not all([self.client_key, self.client_secret]):
            raise ValueError("Missing required environment variables. Please check TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET")

        # Updated endpoints for 2025
        if self.is_development:
            self.console = Console()
            self.console.print("[yellow]Running in development mode[/yellow]")
            self.auth_base_url = "https://open-api.tiktok.com/platform/oauth/connect/"  # Updated to use main API
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"
            if os.getenv('REPL_SLUG') and os.getenv('REPL_OWNER'):
                self.redirect_uri = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co/auth/tiktok/callback"
        else:
            self.console = Console()
            self.console.print("[green]Running in production mode[/green]")
            self.auth_base_url = "https://www.tiktok.com/auth/authorize/"
            self.token_url = "https://open-api.tiktok.com/oauth/access_token/"

    async def _check_endpoint_availability(self, url: str) -> bool:
        """Check if the endpoint is available"""
        try:
            parsed_url = urlparse(url)
            await asyncio.get_event_loop().getaddrinfo(parsed_url.hostname, parsed_url.port or 443)
            return True
        except socket.gaierror:
            self.console.print(f"[yellow]Warning: Unable to resolve {parsed_url.hostname}[/yellow]")
            return False
        except Exception as e:
            self.console.print(f"[yellow]Warning: Error checking {url}: {str(e)}[/yellow]")
            return False

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

        # Check endpoint availability first
        if not await self._check_endpoint_availability(self.token_url):
            self.console.print("[red]TikTok API endpoints are currently unreachable. Please try again later.[/red]")
            return None

        remaining_retries = self.max_retries
        while remaining_retries > 0:
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
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

            except aiohttp.ClientError as e:
                self.console.print(f"[red]Network error during authentication: {str(e)}[/red]")
            except asyncio.TimeoutError:
                self.console.print("[red]Request timed out. TikTok API might be experiencing issues.[/red]")
            except Exception as e:
                self.console.print(f"[red]Unexpected error during authentication: {str(e)}[/red]")

            remaining_retries -= 1
            if remaining_retries > 0:
                await asyncio.sleep(self.retry_delay)
                self.console.print(f"[yellow]Retrying... {remaining_retries} attempts remaining[/yellow]")
            else:
                self.console.print("[red]Maximum number of attempts reached. Please try again later.[/red]")

        return None