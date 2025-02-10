import asyncio
import sys
import os
from rich.console import Console
from downloader import TikTokDownloader
from utils import validate_urls
from auth import TikTokAuth

console = Console()

async def main():
    console.print("[bold green]TikTok Video Downloader[/bold green]")

    # Check if we're in a non-interactive environment (like deployment)
    is_deployed = os.environ.get('REPLIT_DEPLOYMENT') == '1'

    # Initialize auth
    auth = TikTokAuth()

    # In deployment, we don't need the CLI interface
    if is_deployed:
        console.print("[yellow]Running in deployment mode[/yellow]")
        # Assuming access token is provided via environment variable
        access_token = os.environ.get('ACCESS_TOKEN')
        if not access_token:
            console.print("[red]ACCESS_TOKEN environment variable not set. Exiting...[/red]")
            return

        urls = os.environ.get('DOWNLOAD_URLS', '').split(',')
        if not urls:
             console.print("[red]DOWNLOAD_URLS environment variable not set. Exiting...[/red]")
             return

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
        return


    # CLI mode for local development
    while True:
        try:
            # Get auth URL
            auth_url = auth.get_auth_url()
            console.print(f"\n[yellow]Please visit this URL to authenticate:[/yellow]\n{auth_url}")

            # Get the authorization code from user
            auth_code = input("\nEnter the authorization code from the callback URL (or 'q' to quit): ")

            if auth_code.lower() == 'q':
                console.print("[yellow]Exiting...[/yellow]")
                return

            # Get access token
            token_data = await auth.get_access_token(auth_code)
            if not token_data:
                console.print("[red]Authentication failed. Would you like to try again? (y/n)[/red]")
                retry = input("").lower()
                if retry != 'y':
                    return
                continue

            access_token = token_data.get('access_token')
            if not access_token:
                console.print("[red]Invalid token response. Would you like to try again? (y/n)[/red]")
                retry = input("").lower()
                if retry != 'y':
                    return
                continue

            break  # Successfully authenticated

        except Exception as e:
            console.print(f"[red]Authentication error: {str(e)}[/red]")
            console.print("[yellow]Would you like to try again? (y/n)[/yellow]")
            retry = input("").lower()
            if retry != 'y':
                return
            continue

    # Get URLs from command line arguments if provided, otherwise prompt user
    urls = sys.argv[1:] if len(sys.argv) > 1 else []

    if not urls:
        console.print("\nEnter TikTok URLs (one per line, empty line to start downloading):\n")
        while True:
            url = input("Enter URL (or press Enter to start): ")
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