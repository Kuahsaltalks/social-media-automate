"""Command Line Interface for Social Media Content Automation Engine."""
import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from .engine import SocialMediaEngine
from .validator import load_platform_limits

console = Console()

def display_batch_results(data: dict):
    """Render beautiful terminal cards and character validation statistics."""
    console.print()
    console.rule("[bold cyan]Social Media Batch Generation Complete[/bold cyan]")
    
    # 1. Platform Summary Table
    table = Table(title="[bold green]Platform Validation Status[/bold green]", show_header=True, header_style="bold magenta")
    table.add_column("Platform", style="cyan", width=12)
    table.add_column("Character Count", justify="right", width=18)
    table.add_column("Hard Limit", justify="right", width=12)
    table.add_column("Strict Status", justify="center", width=16)
    table.add_column("Hook / Premise", style="dim")

    # X
    x_val = data.get("x", {}).get("validation", {})
    x_status = "[bold green]PASS (<=280)[/bold green]" if x_val.get("is_valid") else f"[bold red]OVER by {x_val.get('overage')}[/bold red]"
    table.add_row("X (Twitter)", f"{x_val.get('length')} chars", "280", x_status, data.get("x", {}).get("hook_type", "Contrarian"))

    # Threads
    th_val = data.get("threads", {}).get("validation", {})
    th_status = "[bold green]PASS (<=500)[/bold green]" if th_val.get("is_valid") else f"[bold red]OVER by {th_val.get('overage')}[/bold red]"
    table.add_row("Threads", f"{th_val.get('length')} chars", "500", th_status, data.get("threads", {}).get("hook_type", "Conversational"))

    # LinkedIn
    li_val = data.get("linkedin", {}).get("validation", {})
    li_status = "[bold green]PASS (<=3000)[/bold green]" if li_val.get("is_valid") else f"[bold red]OVER by {li_val.get('overage')}[/bold red]"
    table.add_row("LinkedIn", f"{li_val.get('length')} chars", "3,000", li_status, data.get("linkedin", {}).get("story_premise", "")[:40] + "...")

    # Carousel
    car_val = data.get("carousel", {}).get("validation", {})
    car_status = "[bold green]PASS (Slides <=220)[/bold green]" if car_val.get("is_valid") else "[bold red]FAIL[/bold red]"
    table.add_row("Carousel", f"{car_val.get('total_slides', 5)} slides", "220 / slide", car_status, data.get("carousel", {}).get("title", "")[:40])

    # Substack Note
    sn_val = data.get("substack_note", {}).get("validation", {})
    sn_status = "[bold green]PASS (<=1000)[/bold green]" if sn_val.get("is_valid") else f"[bold red]OVER by {sn_val.get('overage')}[/bold red]"
    table.add_row("Substack Note", f"{sn_val.get('length')} chars", "1,000", sn_status, data.get("substack_note", {}).get("hook_type", "Reflective"))

    # Substack Newsletter
    table.add_row("Substack Post", "Full Essay", "Long-form", "[bold green]PASS[/bold green]", data.get("substack", {}).get("subject_line", "")[:40])

    console.print(table)
    console.print()

    # 2. Render Previews
    # X Preview
    console.print(Panel(
        f"[bold white]{data.get('x', {}).get('post', '')}[/bold white]\n\n"
        f"[dim]Character Count: {x_val.get('length')}/280 | Hook: {data.get('x', {}).get('hook_type')}[/dim]",
        title="[bold cyan]1. X (Twitter) Post[/bold cyan]",
        border_style="cyan"
    ))

    # Threads Preview
    console.print(Panel(
        f"[bold white]{data.get('threads', {}).get('post', '')}[/bold white]\n\n"
        f"[dim]Character Count: {th_val.get('length')}/500[/dim]",
        title="[bold magenta]2. Meta Threads Post[/bold magenta]",
        border_style="magenta"
    ))

    # LinkedIn Story Preview
    console.print(Panel(
        f"[bold white]{data.get('linkedin', {}).get('post', '')}[/bold white]\n\n"
        f"[dim]Character Count: {li_val.get('length')}/3000 | Hook: {data.get('linkedin', {}).get('hook_type')}[/dim]",
        title="[bold blue]3. LinkedIn Storytelling Post[/bold blue]",
        border_style="blue"
    ))

    # Carousel Preview
    car_slides = data.get("carousel", {}).get("slides", [])
    carousel_text = f"[bold yellow]Deck: {data.get('carousel', {}).get('title')}[/bold yellow]\n\n"
    for s in car_slides:
        carousel_text += f"[bold]Slide {s.get('slide_number')}: {s.get('title')}[/bold] ({len(s.get('content', ''))}/220 chars)\n"
        carousel_text += f"Text: {s.get('content')}\n"
        carousel_text += f"[dim]Design: {s.get('visual_direction')}[/dim]\n\n"
    console.print(Panel(carousel_text.strip(), title="[bold yellow]4. Carousel Slide Deck[/bold yellow]", border_style="yellow"))

    # Substack Note Preview
    sn = data.get("substack_note", {})
    console.print(Panel(
        f"[bold white]{sn.get('post', '')}[/bold white]\n\n"
        f"[dim]Character Count: {sn_val.get('length')}/1000 | Hook: {sn.get('hook_type')}[/dim]",
        title="[bold red]5. Substack Note (Short-form Feed)[/bold red]",
        border_style="red"
    ))

    # Substack Newsletter Preview
    sub = data.get("substack", {})
    sub_text = f"**Subject:** {sub.get('subject_line')}\n\n**Subtitle:** {sub.get('subtitle')}\n\n{sub.get('body_markdown')}"
    console.print(Panel(Markdown(sub_text), title="[bold green]6. Substack Newsletter (Full Article)[/bold green]", border_style="green"))

    if "_saved_to" in data:
        console.print(f"\n[bold green]✔ All content saved to:[/bold green] [underline]{data['_saved_to']}/content.md[/underline]\n")

from .config import get_env_config

def main():
    get_env_config() # Load .env variables
    parser = argparse.ArgumentParser(description="Multi-platform Social Media Automation Engine (Gemini 3.8 / Flash)")
    parser.add_argument("--thought", "-t", type=str, help="Raw dictated thought or research notes")
    parser.add_argument("--file", "-f", type=str, help="Path to markdown or text file containing raw thought")
    parser.add_argument("--model", "-m", type=str, default=None, help="Override model (e.g. gemini-2.5-flash or gemini-3.8-flash)")
    
    # Substack Automation Args
    parser.add_argument("--substack-login", action="store_true", help="Launch browser for one-time Substack login")
    parser.add_argument("--post-substack", type=str, help="Path to batch folder or content.json to create Substack draft")
    parser.add_argument("--subdomain", type=str, default=None, help="Your Subdomain on Substack (e.g. mypub for mypub.substack.com)")
    parser.add_argument("--publish-now", action="store_true", help="Immediately publish on Substack instead of saving as draft")

    # Buffer Automation Args
    parser.add_argument("--check-buffer", action="store_true", help="Check and list connected Buffer channels")
    parser.add_argument("--post-buffer", type=str, help="Path to batch folder or content.json to dispatch to Buffer")
    parser.add_argument("--now", action="store_true", help="Publish immediately right now instead of adding to queue")

    # Telegram Bot
    parser.add_argument("--bot", action="store_true", help="Start background Telegram Bot for mobile dictation & voice notes")

    args = parser.parse_args()

    # Handle Telegram Bot
    if args.bot:
        from .telegram_bot import run_telegram_bot
        run_telegram_bot()
        return

    # Handle Substack Login
    if args.substack_login:
        from .substack_poster import SubstackPoster
        poster = SubstackPoster()
        poster.login_interactive()
        return

    # Handle Substack Posting
    if args.post_substack:
        from .substack_poster import SubstackPoster
        p = Path(args.post_substack)
        json_file = p if p.is_file() else p / "content.json"
        if not json_file.exists():
            console.print(f"[bold red]Error:[/bold red] content.json not found in {args.post_substack}")
            sys.exit(1)
        
        import json
        with open(json_file, "r", encoding="utf-8") as f:
            batch = json.load(f)
        sub_data = batch.get("content", {}).get("substack", {})
        title = sub_data.get("subject_line", "Untitled")
        subtitle = sub_data.get("subtitle", "")
        body = sub_data.get("body_markdown", "")

        console.print(f"[bold cyan]Publishing live to Substack: '{title}'...[/bold cyan]")
        poster = SubstackPoster(subdomain=args.subdomain)
        res = poster.publish_in_running_chrome(title=title, subtitle=subtitle, body_markdown=body, publish_now=True)
        console.print(res)
        return

    # Handle Buffer Check
    if args.check_buffer:
        from .buffer_publisher import BufferPublisher
        pub = BufferPublisher()
        channels = pub.get_connected_channels()
        if not channels:
            console.print("[yellow]No connected channels found or BUFFER_API_KEY is not set in .env[/yellow]")
            console.print("[dim]Get your free API key at: https://publish.buffer.com/settings/api and add it to .env[/dim]")
        else:
            table = Table(title="Connected Buffer Channels", show_header=True)
            table.add_column("Channel Name", style="cyan")
            table.add_column("Platform / Service", style="magenta")
            table.add_column("Channel ID", style="dim")
            for c in channels:
                table.add_row(c.get("name"), c.get("service"), c.get("id"))
            console.print(table)
        return

    # Handle Buffer Dispatch
    if args.post_buffer:
        from .buffer_publisher import BufferPublisher
        p = Path(args.post_buffer)
        json_file = p if p.is_file() else p / "content.json"
        if not json_file.exists():
            console.print(f"[bold red]Error:[/bold red] content.json not found in {args.post_buffer}")
            sys.exit(1)

        import json
        with open(json_file, "r", encoding="utf-8") as f:
            batch = json.load(f)
        
        pub = BufferPublisher()
        content = batch.get("content", {})
        action_name = "Publishing right now to" if args.now else "Queueing to"
        console.print(f"[bold cyan]{action_name} Buffer channels...[/bold cyan]")
        for plat in ["x", "threads", "linkedin"]:
            post_text = content.get(plat, {}).get("post", "")
            if post_text:
                res = pub.publish_post(plat, post_text, share_now=args.now)
                console.print(f"[bold green]✔ {plat.upper()}:[/bold green]", res)
        return

    thought = ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[bold red]Error:[/bold red] File not found: {args.file}")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            thought = f.read().strip()
    elif args.thought:
        thought = args.thought.strip()
    else:
        console.print("[bold cyan]=== Social Media Engine: Dictate / Paste Your Mind's Thoughts ===[/bold cyan]")
        console.print("[dim]Paste your raw thoughts, dictation transcript, or research notes below. Press Ctrl+D (or Ctrl+Z on Windows) when finished:[/dim]\n")
        try:
            thought = sys.stdin.read().strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)

    if not thought:
        console.print("[bold red]Error:[/bold red] No thought or dictation provided.")
        sys.exit(1)

    with console.status("[bold green]Synthesizing thoughts across X, LinkedIn, Threads, Substack & Carousels...[/bold green]", spinner="dots"):
        engine = SocialMediaEngine(model=args.model)
        result = engine.generate_content(thought)

    display_batch_results(result)

if __name__ == "__main__":
    main()
