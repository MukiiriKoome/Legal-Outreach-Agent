import sys
import argparse
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from src.database.db import init_db, SessionLocal
from src.database.models import LawFirm, Lawyer, Meeting, EmailThread
from src.crawler.firm_spider import NairobiFirmSpider
from src.email_service.sender import EmailSender
from src.email_service.listener import InboundEmailListener
from src.agent.email_bot import LegalOutreachBot
from src.config import settings

console = Console()

def cmd_seed(args):
    """Seed the database with top Nairobi corporate law firms."""
    db = SessionLocal()
    try:
        spider = NairobiFirmSpider(db)
        res = spider.seed_database()
        console.print(Panel(
            f"[bold green]Nairobi Legal Directory Ingested Successfully![/]\n\n"
            f"Firms Added: [cyan]{res['firms_added']}[/]\n"
            f"Lawyers Discovered & Verified: [cyan]{res['lawyers_added']}[/]",
            title="Crawler Sync"
        ))
    finally:
        db.close()

def cmd_list(args):
    """List scraped lawyers in Nairobi."""
    db = SessionLocal()
    try:
        lawyers = db.query(Lawyer).all()
        table = Table(title="Nairobi Advocates & Law Firm Leads Pipeline")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Advocate / Partner", style="bold white")
        table.add_column("Role / Title", style="cyan")
        table.add_column("Firm", style="yellow")
        table.add_column("Email", style="green")
        table.add_column("Verified", style="magenta")
        table.add_column("Status", style="bold red")

        for l in lawyers:
            table.add_row(
                str(l.id),
                l.full_name,
                l.title,
                l.firm.name if l.firm else "-",
                l.email,
                "✓ MX Verified" if l.is_verified else "Pending",
                l.status
            )
        console.print(table)
    finally:
        db.close()

def cmd_pitch(args):
    """Draft or send cold outreach email."""
    db = SessionLocal()
    try:
        lawyer = db.query(Lawyer).filter(Lawyer.id == args.id).first()
        if not lawyer:
            console.print(f"[bold red]Lawyer with ID {args.id} not found[/]")
            return
        bot = LegalOutreachBot()
        pitch = bot.generate_initial_pitch(lawyer.full_name, lawyer.title, lawyer.firm.name if lawyer.firm else "Law Firm")
        
        console.print(Panel(
            f"[bold cyan]Subject:[/] {pitch['subject']}\n\n{pitch['body']}",
            title=f"Personalized Pitch for {lawyer.full_name}"
        ))

        if args.send:
            sender = EmailSender(db)
            res = sender.send_initial_pitch(lawyer.id, pitch["subject"], pitch["body"], force=True)
            console.print(f"[bold green]Result:[/] {res}")
    finally:
        db.close()

def cmd_simulate(args):
    """Simulate an incoming email reply from a lawyer."""
    db = SessionLocal()
    try:
        listener = InboundEmailListener(db)
        console.print(f"[bold yellow]Simulating inbound email from:[/] {args.email}")
        console.print(f"[bold white]Body:[/] \"{args.body}\"")

        res = asyncio.run(listener.handle_inbound_reply(
            sender_email=args.email,
            subject="Re: Legal Tech Pitch",
            body=args.body
        ))

        console.print("\n[bold green]Chatbot Processing Result:[/]")
        console.print(f"Intent: [bold magenta]{res.get('intent')}[/]")
        console.print(f"Sentiment: [cyan]{res.get('sentiment')}[/]")
        console.print(f"Meeting Scheduled: [bold red]{res.get('meeting_scheduled')}[/]")
        if res.get('meeting_details'):
            console.print(f"Meeting Details: {res.get('meeting_details')}")
        console.print(Panel(res.get('reply_body', ''), title="AI Generated Reply"))
    finally:
        db.close()

def cmd_serve(args):
    """Start the FastAPI backend and web dashboard."""
    import uvicorn
    console.print(f"[bold green]Starting Wakilify AI Outreach Dashboard on http://{settings.HOST}:{settings.PORT}[/]")
    uvicorn.run("src.web.app:app", host=settings.HOST, port=settings.PORT, reload=False)

def main():
    init_db()
    parser = argparse.ArgumentParser(description="Wakilify AI - Nairobi Legal Tech Investor Outreach Agent")
    subparsers = parser.add_subparsers(dest="command")

    # seed
    subparsers.add_parser("seed", help="Seed Nairobi law firm directory")
    
    # list
    subparsers.add_parser("list", help="List discovered leads and statuses")

    # pitch
    pitch_parser = subparsers.add_parser("pitch", help="Draft or send pitch to a lawyer")
    pitch_parser.add_argument("--id", type=int, required=True, help="Lawyer ID")
    pitch_parser.add_argument("--send", action="store_true", help="Send immediately instead of preview")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Simulate lawyer reply to trigger AI chatbot")
    sim_parser.add_argument("--email", type=str, required=True, help="Lawyer email")
    sim_parser.add_argument("--body", type=str, required=True, help="Reply body text")

    # serve
    subparsers.add_parser("serve", help="Launch web dashboard")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "seed":
        cmd_seed(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "pitch":
        cmd_pitch(args)
    elif args.command == "simulate":
        cmd_simulate(args)
    elif args.command == "serve":
        cmd_serve(args)

if __name__ == "__main__":
    main()
