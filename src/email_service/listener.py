import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.config import settings
from src.database.models import Lawyer, EmailThread, EmailMessage, OptOut
from src.agent.email_bot import LegalOutreachBot
from src.email_service.sender import EmailSender
from src.notifications.scheduler import MeetingScheduler
from src.notifications.alert_manager import FounderAlertManager

class InboundEmailListener:
    """
    Monitors, parses, and acts upon inbound emails received from lawyers.
    """

    def __init__(self, db: Session):
        self.db = db
        self.bot = LegalOutreachBot()
        self.sender = EmailSender(db)
        self.scheduler = MeetingScheduler(db)

    async def handle_inbound_reply(
        self,
        sender_email: str,
        subject: str,
        body: str,
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes an incoming lawyer reply, runs the AI dialogue agent,
        updates thread records, schedules meetings if confirmed, and notifies founder.
        """
        sender_email = sender_email.strip().lower()

        # Find lawyer
        lawyer = self.db.query(Lawyer).filter(Lawyer.email == sender_email).first()
        if not lawyer:
            return {
                "success": False,
                "error": f"No lead registered for email {sender_email}"
            }

        # Find or create email thread
        thread = self.db.query(EmailThread).filter(EmailThread.lawyer_id == lawyer.id).order_by(EmailThread.created_at.desc()).first()
        if not thread:
            thread = EmailThread(
                lawyer_id=lawyer.id,
                subject=subject,
                status="REPLIED"
            )
            self.db.add(thread)
            self.db.flush()
        else:
            thread.status = "REPLIED"
            thread.updated_at = datetime.now(timezone.utc)

        # Record incoming message
        inbound_msg = EmailMessage(
            thread_id=thread.id,
            direction="INBOUND",
            sender=sender_email,
            recipient=settings.FOUNDER_EMAIL,
            subject=subject,
            body=body,
            message_id=message_id,
            in_reply_to=in_reply_to,
            is_approved=True,
            sent_at=datetime.now(timezone.utc)
        )
        self.db.add(inbound_msg)
        self.db.commit()

        # Fetch conversation history for context
        history = []
        for msg in thread.messages:
            history.append({
                "direction": msg.direction,
                "sender": msg.sender,
                "body": msg.body
            })

        # Process with AI Chatbot
        ai_result = self.bot.process_lawyer_reply(
            lawyer_name=lawyer.full_name,
            lawyer_title=lawyer.title,
            firm_name=lawyer.firm.name if lawyer.firm else "Law Firm",
            thread_history=history,
            latest_reply=body
        )

        intent = ai_result.get("intent", "INTERESTED")
        sentiment = ai_result.get("sentiment", "NEUTRAL")
        thread.intent = intent
        thread.sentiment = sentiment

        # 1. Handle Unsubscribe
        if intent == "UNSUBSCRIBE":
            opt = OptOut(email=lawyer.email, reason="Requested unsubscribe via email")
            self.db.add(opt)
            lawyer.status = "OPTED_OUT"
            thread.status = "CLOSED"
            self.db.commit()
            return {
                "success": True,
                "action": "OPT_OUT",
                "message": f"Lead {lawyer.email} marked as opted out"
            }

        # 2. Handle Meeting Detection & Booking
        meeting_info = None
        if ai_result.get("is_meeting_detected") or intent == "MEETING_CONFIRMED":
            proposed_time = ai_result.get("proposed_meeting_time") or "To be finalized via calendar link"
            sched_res = self.scheduler.schedule_meeting(
                lawyer_id=lawyer.id,
                thread_id=thread.id,
                proposed_time_str=proposed_time,
                meeting_notes=f"Auto-scheduled from inbound reply: '{body[:120]}...'"
            )
            meeting_info = sched_res

            # Trigger real-time alert to founder
            await FounderAlertManager.notify_meeting_booked(
                lawyer_name=lawyer.full_name,
                lawyer_title=lawyer.title,
                firm_name=lawyer.firm.name if lawyer.firm else "Nairobi Law Firm",
                lawyer_email=lawyer.email,
                meeting_time=proposed_time,
                meeting_link=sched_res["meeting_link"]
            )

        # 3. Queue or send AI Reply
        reply_body = ai_result.get("reply_body", "")
        send_result = self.sender.send_reply(
            thread_id=thread.id,
            body=reply_body,
            in_reply_to_msg_id=message_id,
            force=not settings.REQUIRE_HUMAN_APPROVAL
        )

        self.db.commit()

        return {
            "success": True,
            "intent": intent,
            "sentiment": sentiment,
            "meeting_scheduled": bool(meeting_info),
            "meeting_details": meeting_info,
            "reply_status": send_result.get("status"),
            "reply_body": reply_body
        }
