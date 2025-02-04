import asyncio
import sys
from rich.console import Console
from rich.prompt import Prompt
from downloader import TikTokDownloader
from utils import validate_urls

console = Console()

async def main():
    console.print("[bold green]TikTok Video Downloader[/bold green]")

    # Get URLs from command line arguments if provided, otherwise prompt user
    urls = sys.argv[1:] if len(sys.argv) > 1 else []

    if not urls:
        console.print("Enter TikTok URLs (one per line, empty line to start downloading):\n")
        while True:
            url = Prompt.ask("Enter URL (or press Enter to start)")
            if not url:
                break
            urls.append(url)

    if not urls:
        console.print("[red]No URLs provided. Exiting...[/red]")
        return

    # Validate URLs
    valid_urls = validate_urls(urls)
    if not valid_urls:
        console.print("[red]No valid URLs found. Exiting...[/red]")
        return

    downloader = TikTokDownloader()
    try:
        await downloader.download_videos(valid_urls)
    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
    finally:
        await downloader.cleanup()

if __name__ == "__main__":
    asyncio.run(main())