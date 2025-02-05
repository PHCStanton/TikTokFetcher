import re
from typing import List, Tuple
from rich.console import Console

console = Console()

def validate_urls(urls: List[str]) -> List[str]:
    """
    Validate TikTok URLs and return only valid ones
    Returns a list of valid URLs
    """
    valid_urls = []
    tiktok_patterns = [
        r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
        r'https?://(?:www\.)?tiktok\.com/v/\d+',
        r'https?://(?:www\.)?tiktok\.com/t/[\w-]+',
        r'https?://(?:vm|vt)\.tiktok\.com/[\w-]+',
        r'https?://(?:www\.)?tiktok\.com/[^\s/]+/video/\d+',
        r'https?://m\.tiktok\.com/v/\d+'
    ]

    for url in urls:
        try:
            url = url.strip()
            is_valid = any(re.match(pattern, url) for pattern in tiktok_patterns)
            if is_valid:
                valid_urls.append(url)
            else:
                console.print(f"[yellow]Warning: Invalid TikTok URL format: {url}[/yellow]")
        except Exception as e:
            console.print(f"[red]Error validating URL {url}: {str(e)}[/red]")
            continue

    if not valid_urls:
        console.print("[red]No valid TikTok URLs found.[/red]")

    return valid_urls