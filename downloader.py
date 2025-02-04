import asyncio
import aiohttp
import os
import re
import json
import time
import random
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.console import Console
from typing import List, Optional, Dict
from urllib.parse import urlparse

class TikTokDownloader:
    def __init__(self):
        self.session = None
        self.console = Console()
        self.max_retries = 3
        self.rate_limit_delay = 1.0
        self.concurrent_downloads = 3
        self.semaphore = asyncio.Semaphore(self.concurrent_downloads)
        self.last_request_time = 0

        # Mobile app headers
        self.mobile_headers = {
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'en-US,en;q=0.9',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-ch-ua-platform': '"iOS"',
            'sec-ch-ua-mobile': '?1',
            'upgrade-insecure-requests': '1'
        }

        # API headers
        self.api_headers = {
            **self.mobile_headers,
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'https://www.tiktok.com',
            'referer': 'https://www.tiktok.com/',
        }

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        if self.session:
            await self.session.close()

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

    def _generate_token(self, url: str) -> str:
        """Generate a token for TikTok API requests"""
        timestamp = str(int(time.time()))
        parsed = urlparse(url)
        path = parsed.path
        return f"verify_{timestamp}_{path.replace('/', '_')}"

    async def _get_video_info(self, video_id: str) -> Optional[Dict]:
        """Get video information using TikTok's mobile API"""
        api_url = f"https://api2-19-h2.musical.ly/aweme/v1/aweme/detail/?aweme_id={video_id}"
        token = self._generate_token(api_url)

        headers = {
            **self.api_headers,
            'x-tt-token': token
        }

        try:
            async with self.session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('aweme_detail', {})
                return None
        except Exception as e:
            self.console.print(f"[yellow]Error getting video info: {str(e)}[/yellow]")
            return None

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

                    # Get video info from API
                    video_info = await self._get_video_info(video_id)
                    if not video_info:
                        raise Exception("Failed to get video info")

                    # Extract video URL from API response
                    video_url = video_info.get('video', {}).get('play_addr', {}).get('url_list', [None])[0]
                    if not video_url:
                        raise Exception("No video URL found in API response")

                    # Download video with proper headers
                    async with self.session.get(video_url, headers=self.mobile_headers) as response:
                        if response.status != 200:
                            raise aiohttp.ClientError(f"HTTP {response.status}")

                        total_size = int(response.headers.get('content-length', 0))
                        progress.update(download_task, total=total_size)

                        with open(filename, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                progress.update(download_task, advance=len(chunk))

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
        """Implement rate limiting between requests with jitter"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            jitter = random.uniform(0, 0.5)  # Add random delay between 0-0.5 seconds
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request + jitter)
        self.last_request_time = time.time()

    async def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        if 'vm.tiktok.com' in url or 't.tiktok.com' in url:
            try:
                async with self.session.get(url, headers=self.mobile_headers, allow_redirects=True) as response:
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