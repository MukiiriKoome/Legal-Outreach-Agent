from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.config import settings
from src.database.db import get_db, init_db
from src.database.models import LawFirm, Lawyer, EmailThread, EmailMessage, Meeting, OptOut
from src.crawler.firm_spider import NairobiFirmSpider
from src.crawler.contact_verifier import verify_lead_email
from src.agent.email_bot import LegalOutreachBot
from src.email_service.sender import EmailSender
from src.email_service.listener import InboundEmailListener
from src.notifications.scheduler import MeetingScheduler
from src.notifications.alert_manager import FounderAlertManager

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Nairobi Legal Tech Investor Outreach Agent",
    description="Automated webcrawling, scraping, cold outreach, and conversational AI scheduling for law firm partners in Nairobi",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request / Response Models ---
class LeadOutreachRequest(BaseModel):
    lawyer_id: int
    force_send: bool = False

class SimulateReplyRequest(BaseModel):
    lawyer_email: str
    subject: str = "Re: Legal Tech Pitch"
    body: str

class SettingsUpdateRequest(BaseModel):
    STARTUP_NAME: Optional[str] = None
    FOUNDER_NAME: Optional[str] = None
    FOUNDER_EMAIL: Optional[str] = None
    CALENDLY_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    EMAIL_MODE: Optional[str] = None
    REQUIRE_HUMAN_APPROVAL: Optional[bool] = None

class ScrapeUrlRequest(BaseModel):
    url: str
    firm_name: str

# --- API Endpoints ---

@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_firms = db.query(func.count(LawFirm.id)).scalar() or 0
    total_lawyers = db.query(func.count(Lawyer.id)).scalar() or 0
    verified_lawyers = db.query(func.count(Lawyer.id)).filter(Lawyer.is_verified == True).scalar() or 0
    contacted = db.query(func.count(Lawyer.id)).filter(Lawyer.status.in_(["CONTACTED", "ENGAGED", "MEETING_BOOKED"])).scalar() or 0
    pending_approval = db.query(func.count(EmailMessage.id)).filter(EmailMessage.is_approved == False).scalar() or 0
    meetings_booked = db.query(func.count(Meeting.id)).scalar() or 0
    opt_outs = db.query(func.count(OptOut.id)).scalar() or 0

    return {
        "total_firms": total_firms,
        "total_leads": total_lawyers,
        "verified_leads": verified_lawyers,
        "contacted": contacted,
        "pending_approval": pending_approval,
        "meetings_booked": meetings_booked,
        "opt_outs": opt_outs
    }

@app.get("/api/leads")
def list_leads(
    status: Optional[str] = None,
    firm: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Lawyer)
    if status:
        query = query.filter(Lawyer.status == status)
    if firm:
        query = query.join(LawFirm).filter(LawFirm.name.ilike(f"%{firm}%"))
    if search:
        query = query.filter(
            (Lawyer.full_name.ilike(f"%{search}%")) | (Lawyer.email.ilike(f"%{search}%"))
        )
    lawyers = query.order_by(Lawyer.id.desc()).limit(limit).all()

    results = []
    for l in lawyers:
        results.append({
            "id": l.id,
            "full_name": l.full_name,
            "title": l.title,
            "email": l.email,
            "phone": l.phone,
            "firm_name": l.firm.name if l.firm else "Unknown",
            "firm_address": l.firm.address if l.firm else "",
            "is_verified": l.is_verified,
            "status": l.status,
            "bio": l.bio
        })
    return results

@app.post("/api/crawler/seed")
def seed_directory(db: Session = Depends(get_db)):
    spider = NairobiFirmSpider(db)
    counts = spider.seed_database()
    return {"success": True, "message": "Nairobi law firm directory seeded", "details": counts}

@app.post("/api/crawler/scrape-url")
async def scrape_firm_url(req: ScrapeUrlRequest, db: Session = Depends(get_db)):
    spider = NairobiFirmSpider(db)
    extracted = await spider.crawl_firm_url(req.url, req.firm_name)
    return {"success": True, "count": len(extracted), "extracted": extracted}

@app.post("/api/leads/{lawyer_id}/draft-pitch")
def preview_pitch_draft(lawyer_id: int, db: Session = Depends(get_db)):
    lawyer = db.query(Lawyer).filter(Lawyer.id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail="Lawyer not found")
    bot = LegalOutreachBot()
    pitch = bot.generate_initial_pitch(
        lawyer_name=lawyer.full_name,
        lawyer_title=lawyer.title,
        firm_name=lawyer.firm.name if lawyer.firm else "Law Firm"
    )
    return pitch

@app.post("/api/leads/{lawyer_id}/send-pitch")
def send_initial_pitch(lawyer_id: int, force: bool = False, db: Session = Depends(get_db)):
    lawyer = db.query(Lawyer).filter(Lawyer.id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail="Lawyer not found")
    bot = LegalOutreachBot()
    pitch = bot.generate_initial_pitch(
        lawyer_name=lawyer.full_name,
        lawyer_title=lawyer.title,
        firm_name=lawyer.firm.name if lawyer.firm else "Law Firm"
    )
    sender = EmailSender(db)
    res = sender.send_initial_pitch(lawyer_id, pitch["subject"], pitch["body"], force=force)
    return res

@app.get("/api/queue")
def list_pending_approval_queue(db: Session = Depends(get_db)):
    messages = db.query(EmailMessage).filter(EmailMessage.is_approved == False).all()
    queue = []
    for m in messages:
        queue.append({
            "id": m.id,
            "thread_id": m.thread_id,
            "recipient": m.recipient,
            "subject": m.subject,
            "body": m.body,
            "sent_at": m.sent_at.isoformat()
        })
    return queue

@app.post("/api/queue/{message_id}/approve")
def approve_pending_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(EmailMessage).filter(EmailMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    sender = EmailSender(db)
    delivery = sender._deliver(msg.recipient, msg.subject, msg.body, msg.message_id or "id")
    if delivery.get("success"):
        msg.is_approved = True
        if msg.thread and msg.thread.lawyer:
            msg.thread.lawyer.status = "CONTACTED"
            msg.thread.status = "SENT"
        db.commit()
        return {"success": True, "message": "Email approved and sent"}
    else:
        raise HTTPException(status_code=500, detail=delivery.get("error", "Delivery failed"))

@app.get("/api/threads")
def list_conversation_threads(db: Session = Depends(get_db)):
    threads = db.query(EmailThread).order_by(EmailThread.updated_at.desc()).all()
    results = []
    for t in threads:
        results.append({
            "id": t.id,
            "lawyer_id": t.lawyer_id,
            "lawyer_name": t.lawyer.full_name if t.lawyer else "Unknown",
            "lawyer_email": t.lawyer.email if t.lawyer else "",
            "firm_name": t.lawyer.firm.name if t.lawyer and t.lawyer.firm else "",
            "subject": t.subject,
            "status": t.status,
            "sentiment": t.sentiment,
            "intent": t.intent,
            "updated_at": t.updated_at.isoformat(),
            "message_count": len(t.messages)
        })
    return results

@app.get("/api/threads/{thread_id}")
def get_thread_details(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(EmailThread).filter(EmailThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    messages = []
    for m in thread.messages:
        messages.append({
            "id": m.id,
            "direction": m.direction,
            "sender": m.sender,
            "recipient": m.recipient,
            "subject": m.subject,
            "body": m.body,
            "is_approved": m.is_approved,
            "sent_at": m.sent_at.isoformat()
        })

    return {
        "id": thread.id,
        "lawyer_name": thread.lawyer.full_name if thread.lawyer else "Unknown",
        "lawyer_email": thread.lawyer.email if thread.lawyer else "",
        "firm_name": thread.lawyer.firm.name if thread.lawyer and thread.lawyer.firm else "",
        "subject": thread.subject,
        "status": thread.status,
        "sentiment": thread.sentiment,
        "intent": thread.intent,
        "messages": messages
    }

@app.post("/api/threads/simulate-reply")
async def simulate_inbound_lawyer_reply(req: SimulateReplyRequest, db: Session = Depends(get_db)):
    """
    Simulator allowing you to test lawyer responses (e.g. asking for deck, proposing Thursday 3pm meeting)
    and see the AI chatbot reply, schedule the meeting, and send notifications.
    """
    listener = InboundEmailListener(db)
    result = await listener.handle_inbound_reply(
        sender_email=req.lawyer_email,
        subject=req.subject,
        body=req.body
    )
    return result

@app.get("/api/meetings")
def list_meetings(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    results = []
    for m in meetings:
        results.append({
            "id": m.id,
            "lawyer_name": m.lawyer.full_name if m.lawyer else "Unknown",
            "firm_name": m.lawyer.firm.name if m.lawyer and m.lawyer.firm else "Unknown",
            "lawyer_email": m.lawyer.email if m.lawyer else "",
            "title": m.title,
            "scheduled_for": m.scheduled_for,
            "meeting_link": m.meeting_link,
            "status": m.status,
            "created_at": m.created_at.isoformat()
        })
    return results

@app.get("/api/settings")
def get_app_settings():
    return {
        "STARTUP_NAME": settings.STARTUP_NAME,
        "FOUNDER_NAME": settings.FOUNDER_NAME,
        "FOUNDER_EMAIL": settings.FOUNDER_EMAIL,
        "CALENDLY_URL": settings.CALENDLY_URL,
        "EMAIL_MODE": settings.EMAIL_MODE,
        "REQUIRE_HUMAN_APPROVAL": settings.REQUIRE_HUMAN_APPROVAL,
        "GEMINI_MODEL": settings.GEMINI_MODEL,
        "HAS_GEMINI_KEY": bool(settings.GEMINI_API_KEY)
    }

@app.post("/api/settings")
def update_app_settings(req: SettingsUpdateRequest):
    if req.STARTUP_NAME is not None:
        settings.STARTUP_NAME = req.STARTUP_NAME
    if req.FOUNDER_NAME is not None:
        settings.FOUNDER_NAME = req.FOUNDER_NAME
    if req.FOUNDER_EMAIL is not None:
        settings.FOUNDER_EMAIL = req.FOUNDER_EMAIL
    if req.CALENDLY_URL is not None:
        settings.CALENDLY_URL = req.CALENDLY_URL
    if req.GEMINI_API_KEY is not None:
        settings.GEMINI_API_KEY = req.GEMINI_API_KEY
    if req.EMAIL_MODE is not None:
        settings.EMAIL_MODE = req.EMAIL_MODE
    if req.REQUIRE_HUMAN_APPROVAL is not None:
        settings.REQUIRE_HUMAN_APPROVAL = req.REQUIRE_HUMAN_APPROVAL
    return {"success": True, "message": "Settings updated in runtime"}

# Serve static dashboard
static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/")
def serve_dashboard():
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Nairobi Legal Outreach Agent</h1><p>Dashboard loading...</p>")
