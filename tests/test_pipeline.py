import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, LawFirm, Lawyer, EmailThread, Meeting
from src.crawler.firm_spider import NairobiFirmSpider
from src.email_service.sender import EmailSender
from src.email_service.listener import InboundEmailListener
from src.notifications.scheduler import MeetingScheduler

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

@pytest.mark.asyncio
async def test_full_investor_outreach_pipeline(test_db):
    # 1. Seed Directory
    spider = NairobiFirmSpider(test_db)
    spider.seed_database()

    lawyer = test_db.query(Lawyer).first()
    assert lawyer is not None

    # 2. Send Initial Outreach
    sender = EmailSender(test_db)
    pitch_res = sender.send_initial_pitch(
        lawyer_id=lawyer.id,
        subject=f"Legal Tech Angel Advisory | {lawyer.firm.name}",
        body="Dear Partner, we are building Wakilify AI. Would you be open to an introductory meeting?",
        force=True
    )
    assert pitch_res["success"] is True

    # 3. Simulate Lawyer asking for Deck
    listener = InboundEmailListener(test_db)
    reply1 = await listener.handle_inbound_reply(
        sender_email=lawyer.email,
        subject="Re: Legal Tech Angel Advisory",
        body="Hi Alex, this caught my attention. Could you send over your deck and traction in Nairobi?"
    )
    assert reply1["success"] is True
    assert reply1["intent"] == "ASKING_QUESTIONS"

    # 4. Simulate Lawyer confirming Meeting
    reply2 = await listener.handle_inbound_reply(
        sender_email=lawyer.email,
        subject="Re: Legal Tech Angel Advisory",
        body="Looks very strong. Let's meet Friday at 10:00 AM on Google Meet."
    )
    assert reply2["success"] is True
    assert reply2["meeting_scheduled"] is True

    # Verify meeting in database
    meeting = test_db.query(Meeting).filter(Meeting.lawyer_id == lawyer.id).first()
    assert meeting is not None
    assert "Friday" in meeting.scheduled_for
    assert lawyer.status == "MEETING_BOOKED"
