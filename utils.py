import re
from typing import List

def validate_urls(urls: List[str]) -> List[str]:
    """
    Validate TikTok URLs and return only valid ones
    """
    valid_urls = []
    tiktok_patterns = [
        r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
        r'https?://(?:www\.)?tiktok\.com/v/\d+',
        r'https?://(?:www\.)?tiktok\.com/t/\w+',
        r'https?://vm\.tiktok\.com/\w+',
    ]
    
    for url in urls:
        url = url.strip()
        is_valid = any(re.match(pattern, url) for pattern in tiktok_patterns)
        if is_valid:
            valid_urls.append(url)
            
    return valid_urls
