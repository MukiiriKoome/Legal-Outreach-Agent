import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.config import settings
from src.database.models import Lawyer, Meeting, EmailThread

class MeetingScheduler:
    """
    Handles meeting creation, calendar invite generation (.ics),
    and synchronization with the founder's schedule.
    """

    def __init__(self, db: Session):
        self.db = db

    def schedule_meeting(
        self,
        lawyer_id: int,
        thread_id: Optional[int],
        proposed_time_str: str,
        meeting_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Creates a confirmed meeting record and generates calendar credentials.
        """
        lawyer = self.db.query(Lawyer).filter(Lawyer.id == lawyer_id).first()
        if not lawyer:
            return {"success": False, "error": "Lawyer not found"}

        title = f"Investor Intro: {settings.STARTUP_NAME} & {lawyer.full_name} ({lawyer.firm.name})"
        meeting_link = f"https://meet.google.com/nbo-{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}"

        meeting = Meeting(
            lawyer_id=lawyer.id,
            thread_id=thread_id,
            title=title,
            scheduled_for=proposed_time_str,
            meeting_link=meeting_link,
            notes=meeting_notes,
            status="CONFIRMED",
            notified_founder=False
        )
        self.db.add(meeting)

        # Update lawyer and thread statuses
        lawyer.status = "MEETING_BOOKED"
        if thread_id:
            thread = self.db.query(EmailThread).filter(EmailThread.id == thread_id).first()
            if thread:
                thread.status = "MEETING_BOOKED"

        self.db.commit()

        # Generate .ics format text
        ics_content = self.generate_ics(
            summary=title,
            description=f"Introductory discussion on legal tech angel investment in {settings.STARTUP_NAME}.\nGoogle Meet: {meeting_link}",
            attendee_email=lawyer.email,
            attendee_name=lawyer.full_name,
            scheduled_str=proposed_time_str
        )

        return {
            "success": True,
            "meeting_id": meeting.id,
            "title": title,
            "scheduled_for": proposed_time_str,
            "meeting_link": meeting_link,
            "ics_content": ics_content
        }

    def generate_ics(
        self,
        summary: str,
        description: str,
        attendee_email: str,
        attendee_name: str,
        scheduled_str: str
    ) -> str:
        """
        Generates standard iCalendar (.ics) invite string.
        """
        now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        uid = f"{uuid.uuid4()}@wakilify.co.ke"

        return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//{settings.STARTUP_NAME}//Investor Meetings//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now_stamp}
SUMMARY:{summary}
DESCRIPTION:{description}
ORGANIZER;CN="{settings.FOUNDER_NAME}":mailto:{settings.FOUNDER_EMAIL}
ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN="{attendee_name}":mailto:{attendee_email}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
