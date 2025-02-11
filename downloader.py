import asyncio
import aiohttp
import os
import re
import json
import time
import random # Added for jitter in rate limiting
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.console import Console
from typing import List, Optional, Dict, Any
from datetime import datetime

class TikTokDownloader:
    def __init__(self, access_token=None):
        self.session = None
        self.console = Console()
        self.max_retries = 3
        self.access_token = access_token
        self.rate_limit_delay = 2.5  # Increased from 1.0 to 2.5 seconds
        self.concurrent_downloads = 2  # Reduced from 3 to 2 for better stability
        self.semaphore = asyncio.Semaphore(self.concurrent_downloads)
        self.last_request_time = 0
        self.api_base_url = "https://open.tiktokapis.com/v2"

    async def get_user_videos(self, max_count: int = 30, cursor: int = 0, sort_type: str = "latest") -> Dict[str, Any]:
        """Fetch videos from the user's profile with sorting options"""
        if not self.access_token:
            raise ValueError("Access token is required to fetch user videos")

        await self.init_session()

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # Map sort type to API parameters
            sort_params = {
                "latest": {"sort_type": "create_time", "order": "desc"},
                "oldest": {"sort_type": "create_time", "order": "asc"},
                "most_liked": {"sort_type": "likes", "order": "desc"},
                "most_viewed": {"sort_type": "views", "order": "desc"}
            }

            sort_config = sort_params.get(sort_type, sort_params["latest"])

            params = {
                "max_count": max_count,
                "cursor": cursor,
                **sort_config
            }

            url = f"{self.api_base_url}/video/list/"
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "videos": [{
                            "id": video["id"],
                            "title": video.get("title", ""),
                            "cover_url": video.get("cover_url", ""),
                            "share_url": video.get("share_url", ""),
                            "create_time": datetime.fromtimestamp(video.get("create_time", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                            "stats": {
                                "likes": video.get("statistics", {}).get("like_count", 0),
                                "views": video.get("statistics", {}).get("view_count", 0),
                                "shares": video.get("statistics", {}).get("share_count", 0)
                            },
                            "hashtags": [tag["name"] for tag in video.get("hashtags", [])]
                        } for video in data.get("videos", [])],
                        "cursor": data.get("cursor", 0),
                        "has_more": data.get("has_more", False)
                    }
                else:
                    error_data = await response.json()
                    raise Exception(f"Failed to fetch videos: {error_data.get('error', 'Unknown error')}")

        except Exception as e:
            self.console.print(f"[red]Error fetching user videos: {str(e)}[/red]")
            return {"videos": [], "cursor": cursor, "has_more": False}

    async def init_session(self):
        """Initialize aiohttp session if not already initialized"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.mobile_headers,
                compress=True
            )
        return self.session

    async def cleanup(self):
        if self.session:
            await self.session.close()

    async def _get_video_url(self, url: str) -> Optional[str]:
        """Get the actual video URL from TikTok"""
        session = await self.init_session()
        try:
            await self._rate_limit()  # Ensure rate limiting before request

            # Try mobile user agent first
            async with session.get(url, allow_redirects=True, timeout=30) as response:
                if response.status == 429:  # Rate limit hit
                    self.console.print("[yellow]Rate limit hit, waiting...[/yellow]")
                    await asyncio.sleep(5)
                    return None
                elif response.status != 200:
                    # If mobile fails, try desktop user agent
                    async with aiohttp.ClientSession(headers=self.desktop_headers) as desktop_session:
                        async with desktop_session.get(url, timeout=30) as desktop_response:
                            if desktop_response.status != 200:
                                self.console.print(f"[red]Failed to fetch URL: HTTP {desktop_response.status}[/red]")
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
                            async with session.head(video_url) as vid_response:
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

    async def download_videos(self, video_ids: List[str]):
        """Download multiple videos by their IDs"""
        await self.init_session()
        os.makedirs("downloads", exist_ok=True)

        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            tasks = []
            for video_id in video_ids:
                task = asyncio.create_task(self._download_single_video(video_id, progress))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for video_id, result in zip(video_ids, results):
                if isinstance(result, Exception):
                    self.console.print(f"[red]Failed to download video {video_id}: {str(result)}[/red]")

    async def _download_single_video(self, video_id: str, progress):
        session = await self.init_session()
        async with self.semaphore:

            filename = f"downloads/tiktok_{video_id}.mp4"
            download_task = progress.add_task(
                f"Downloading {video_id}",
                total=None
            )

            for retry in range(self.max_retries):
                try:
                    await self._rate_limit()
                    #Now using video_id to fetch the share_url
                    user_videos = await self.get_user_videos(max_count=1, sort_type="latest") # Adjust as needed
                    video_url = None
                    if user_videos and user_videos["videos"]:
                        video_url = user_videos["videos"][0]["share_url"]

                    if not video_url:
                        progress.update(download_task, description=f"[red]Failed to get video URL for {video_id}[/red]")
                        return

                    async with session.get(video_url) as response:
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
        """Implement improved rate limiting with jitter"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            jitter = random.uniform(0, 0.5)  # Add random jitter between 0-0.5 seconds
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request + jitter)
        self.last_request_time = time.time()

    async def _extract_video_id(self, url: str) -> Optional[str]:
        session = await self.init_session()
        # First, resolve any shortened URLs
        if 'vm.tiktok.com' in url or 't.tiktok.com' in url:
            try:
                async with session.get(url, allow_redirects=True) as response:
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

    mobile_headers = {
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
    desktop_headers = {
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