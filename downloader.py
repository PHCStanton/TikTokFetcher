import asyncio
import aiohttp
import os
import re
import json
import time
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.console import Console
from typing import List, Optional, Dict

class TikTokDownloader:
    def __init__(self):
        self.session = None
        self.console = Console()
        self.max_retries = 3
        self.rate_limit_delay = 1.0  # Delay between requests in seconds
        self.concurrent_downloads = 3  # Maximum concurrent downloads
        self.semaphore = asyncio.Semaphore(self.concurrent_downloads)
        self.last_request_time = 0
        self.mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }
        self.desktop_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers=self.mobile_headers,
                compress=True
            )

    async def cleanup(self):
        if self.session:
            await self.session.close()

    async def _get_video_url(self, url: str) -> Optional[str]:
        """Get the actual video URL from TikTok"""
        try:
            # Try mobile user agent first
            async with self.session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    # If mobile fails, try desktop user agent
                    async with aiohttp.ClientSession(headers=self.desktop_headers) as desktop_session:
                        async with desktop_session.get(url) as desktop_response:
                            if desktop_response.status != 200:
                                return None
                            content = await desktop_response.text()
                else:
                    content = await response.text()

                self.console.print("[yellow]Attempting to extract video URL...[/yellow]")

                # Look for various patterns of video URLs
                patterns = [
                    r'{"playAddr":"([^"]+)"',
                    r'{"downloadAddr":"([^"]+)"',
                    r'"playAddr":"([^"]+)"',
                    r'"downloadAddr":"([^"]+)"',
                    r'"playUrl":"([^"]+)"',
                    r'<video[^>]+src="([^"]+\.mp4)"',
                    r'https?://[^\s<>"]+?\.mp4(?:[^"\s<>]*)'
                ]

                for pattern in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        video_url = match.group(1) if not pattern.endswith('mp4(?:[^"\s<>]*)') else match.group(0)
                        video_url = video_url.replace(r'\u002F', '/').replace('\\/', '/')
                        if video_url.startswith('//'):
                            video_url = 'https:' + video_url

                        # Verify if the URL is accessible
                        try:
                            async with self.session.head(video_url) as vid_response:
                                if vid_response.status == 200:
                                    self.console.print(f"[green]Found valid video URL[/green]")
                                    return video_url
                        except:
                            continue

                self.console.print("[yellow]Warning: Could not find valid video URL[/yellow]")
                return None

        except Exception as e:
            self.console.print(f"[red]Error extracting video URL: {str(e)}[/red]")
            return None

    async def download_videos(self, urls: List[str]):
        await self.init_session()
        os.makedirs("downloads", exist_ok=True)

        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            tasks = []
            for url in urls:
                task = asyncio.create_task(self._download_single_video(url, progress))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    self.console.print(f"[red]Failed to download {url}: {str(result)}[/red]")

    async def _download_single_video(self, url: str, progress):
        async with self.semaphore:
            video_id = await self._extract_video_id(url)
            if not video_id:
                self.console.print(f"[red]Invalid URL: {url}[/red]")
                return

            filename = f"downloads/tiktok_{video_id}.mp4"
            download_task = progress.add_task(
                f"Downloading {video_id}",
                total=None
            )

            for retry in range(self.max_retries):
                try:
                    await self._rate_limit()
                    video_url = await self._get_video_url(url)

                    if not video_url:
                        progress.update(download_task, description=f"[red]Failed to get video URL for {video_id}[/red]")
                        return

                    async with self.session.get(video_url) as response:
                        if response.status != 200:
                            raise aiohttp.ClientError(f"HTTP {response.status}")

                        total_size = int(response.headers.get('content-length', 0))
                        progress.update(download_task, total=total_size)

                        with open(filename, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                progress.update(download_task, advance=len(chunk))

                        # Verify download
                        if os.path.getsize(filename) == total_size:
                            progress.update(download_task, description=f"[green]Completed {video_id}[/green]")
                            return
                        else:
                            raise Exception("Download verification failed")

                except Exception as e:
                    if retry < self.max_retries - 1:
                        delay = (retry + 1) * 2
                        progress.update(download_task, description=f"[yellow]Retrying {video_id} in {delay}s ({str(e)})[/yellow]")
                        await asyncio.sleep(delay)
                    else:
                        progress.update(download_task, description=f"[red]Failed {video_id}: {str(e)}[/red]")

    async def _rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request)
        self.last_request_time = time.time()

    async def _extract_video_id(self, url: str) -> Optional[str]:
        # First, resolve any shortened URLs
        if 'vm.tiktok.com' in url or 't.tiktok.com' in url:
            try:
                async with self.session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        url = str(response.url)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not resolve shortened URL: {str(e)}[/yellow]")

        patterns = [
            r'video/(\d+)',
            r'v/(\d+)',
            r'@[\w.-]+/video/(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None