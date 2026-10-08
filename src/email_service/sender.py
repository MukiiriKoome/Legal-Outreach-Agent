import smtplib
import uuid
import time
import random
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.config import settings
from src.database.models import Lawyer, EmailThread, EmailMessage, OptOut

class EmailSender:
    """
    Handles outbound cold emails and follow-ups with throttling,
    threading headers, and simulation/SMTP support.
    """

    def __init__(self, db: Session):
        self.db = db

    def send_initial_pitch(self, lawyer_id: int, subject: str, body: str, force: bool = False) -> Dict[str, Any]:
        """
        Sends or queues the initial cold outreach email to a verified lawyer.
        """
        lawyer = self.db.query(Lawyer).filter(Lawyer.id == lawyer_id).first()
        if not lawyer:
            return {"success": False, "error": "Lawyer not found"}

        # Verify opt-out status
        opted = self.db.query(OptOut).filter(OptOut.email == lawyer.email).first()
        if opted:
            return {"success": False, "error": "Lawyer has opted out"}

        # Check existing thread
        thread = self.db.query(EmailThread).filter(EmailThread.lawyer_id == lawyer.id).first()
        if not thread:
            thread = EmailThread(
                lawyer_id=lawyer.id,
                subject=subject,
                status="SENT" if not settings.REQUIRE_HUMAN_APPROVAL or force else "PENDING_APPROVAL"
            )
            self.db.add(thread)
            self.db.flush()

        # Format message with compliant unsubscribe footer
        formatted_body = self._attach_compliance_footer(body, lawyer.email)
        message_id = f"<{uuid.uuid4()}@{settings.SMTP_HOST or 'wakilify.co.ke'}>"

        msg_record = EmailMessage(
            thread_id=thread.id,
            direction="OUTBOUND",
            sender=settings.FOUNDER_EMAIL,
            recipient=lawyer.email,
            subject=subject,
            body=formatted_body,
            message_id=message_id,
            is_approved=not settings.REQUIRE_HUMAN_APPROVAL or force,
            sent_at=datetime.now(timezone.utc)
        )
        self.db.add(msg_record)

        if settings.REQUIRE_HUMAN_APPROVAL and not force:
            lawyer.status = "PENDING_APPROVAL"
            self.db.commit()
            return {
                "success": True,
                "status": "QUEUED_FOR_APPROVAL",
                "thread_id": thread.id,
                "message": "Email drafted and waiting for founder approval in dashboard"
            }

        # Deliver via SMTP or Mock
        delivery_res = self._deliver(lawyer.email, subject, formatted_body, message_id)
        if delivery_res.get("success"):
            lawyer.status = "CONTACTED"
            thread.status = "SENT"
            self.db.commit()
            return {
                "success": True,
                "status": "DELIVERED",
                "thread_id": thread.id,
                "message_id": message_id
            }
        else:
            self.db.rollback()
            return delivery_res

    def send_reply(self, thread_id: int, body: str, in_reply_to_msg_id: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        Sends an automated or approved follow-up reply in an active thread.
        """
        thread = self.db.query(EmailThread).filter(EmailThread.id == thread_id).first()
        if not thread:
            return {"success": False, "error": "Thread not found"}

        lawyer = thread.lawyer
        subject = f"Re: {thread.subject}" if not thread.subject.startswith("Re:") else thread.subject
        formatted_body = self._attach_compliance_footer(body, lawyer.email)
        message_id = f"<{uuid.uuid4()}@{settings.SMTP_HOST or 'wakilify.co.ke'}>"

        msg_record = EmailMessage(
            thread_id=thread.id,
            direction="OUTBOUND",
            sender=settings.FOUNDER_EMAIL,
            recipient=lawyer.email,
            subject=subject,
            body=formatted_body,
            message_id=message_id,
            in_reply_to=in_reply_to_msg_id,
            is_approved=not settings.REQUIRE_HUMAN_APPROVAL or force,
            sent_at=datetime.now(timezone.utc)
        )
        self.db.add(msg_record)

        if settings.REQUIRE_HUMAN_APPROVAL and not force:
            self.db.commit()
            return {
                "success": True,
                "status": "QUEUED_FOR_APPROVAL",
                "message": "Reply queued for founder approval"
            }

        delivery_res = self._deliver(lawyer.email, subject, formatted_body, message_id, in_reply_to_msg_id)
        if delivery_res.get("success"):
            thread.status = "IN_CONVERSATION"
            thread.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return {"success": True, "status": "DELIVERED", "message_id": message_id}
        else:
            self.db.rollback()
            return delivery_res

    def _deliver(self, recipient: str, subject: str, body: str, message_id: str, in_reply_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes physical delivery or mock log delivery.
        """
        if settings.EMAIL_MODE == "smtp" and settings.SMTP_PASSWORD:
            try:
                msg = MIMEMultipart()
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.FOUNDER_EMAIL}>"
                msg["To"] = recipient
                msg["Subject"] = subject
                msg["Message-ID"] = message_id
                if in_reply_to:
                    msg["In-Reply-To"] = in_reply_to
                    msg["References"] = in_reply_to

                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.FOUNDER_EMAIL, [recipient], msg.as_string())
                
                # Apply anti-spam jitter delay
                time.sleep(random.uniform(settings.MIN_DELAY_SECONDS, settings.MAX_DELAY_SECONDS))
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": f"SMTP Error: {str(e)}"}
        else:
            # Safe mock delivery (ideal for testing & sandbox demo)
            print(f"\n[MOCK EMAIL DELIVERED] >>> To: {recipient} | Subject: {subject} | MsgID: {message_id}\n")
            return {"success": True, "mode": "MOCK"}

    def _attach_compliance_footer(self, body: str, email: str) -> str:
        """
        Appends mandatory unsubscribe and data compliance disclosure
        under Kenya Data Protection Act 2019.
        """
        footer = f"""

---
Notice: You received this business communication as a legal practitioner in Nairobi. If you do not wish to receive further updates, simply reply with 'UNSUBSCRIBE' or email optout@wakilify.co.ke. 
{settings.STARTUP_NAME} | Nairobi, Kenya | Dedicated to Law Firm Efficiency
"""
        return body.rstrip() + footer
