import asyncio
import sys
from rich.console import Console
from rich.prompt import Prompt
from downloader import TikTokDownloader
from utils import validate_urls
from auth import TikTokAuth

console = Console()

async def main():
    console.print("[bold green]TikTok Video Downloader[/bold green]")

    # Initialize auth
    auth = TikTokAuth()

    while True:
        try:
            # Get auth URL
            auth_url = auth.get_auth_url()
            console.print(f"\n[yellow]Please visit this URL to authenticate:[/yellow]\n{auth_url}")

            # Get the authorization code from user
            auth_code = Prompt.ask("\nEnter the authorization code from the callback URL (or 'q' to quit)")

            if auth_code.lower() == 'q':
                console.print("[yellow]Exiting...[/yellow]")
                return

            # Get access token
            token_data = await auth.get_access_token(auth_code)
            if not token_data:
                console.print("[red]Authentication failed. Would you like to try again? (y/n)[/red]")
                retry = Prompt.ask("").lower()
                if retry != 'y':
                    return
                continue

            access_token = token_data.get('access_token')
            if not access_token:
                console.print("[red]Invalid token response. Would you like to try again? (y/n)[/red]")
                retry = Prompt.ask("").lower()
                if retry != 'y':
                    return
                continue

            break  # Successfully authenticated

        except Exception as e:
            console.print(f"[red]Authentication error: {str(e)}[/red]")
            console.print("[yellow]Would you like to try again? (y/n)[/yellow]")
            retry = Prompt.ask("").lower()
            if retry != 'y':
                return
            continue

    # Get URLs from command line arguments if provided, otherwise prompt user
    urls = sys.argv[1:] if len(sys.argv) > 1 else []

    if not urls:
        console.print("\nEnter TikTok URLs (one per line, empty line to start downloading):\n")
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

    downloader = TikTokDownloader(access_token=access_token)
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