from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class LawFirm(Base):
    __tablename__ = "law_firms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="Nairobi")
    practice_areas: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    lawyers: Mapped[List["Lawyer"]] = relationship("Lawyer", back_populates="firm", cascade="all, delete-orphan")


class Lawyer(Base):
    __tablename__ = "lawyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    firm_id: Mapped[int] = mapped_column(Integer, ForeignKey("law_firms.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Partner")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="NEW")  
    # NEW, VERIFIED, PENDING_APPROVAL, CONTACTED, ENGAGED, MEETING_BOOKED, NOT_INTERESTED, OPTED_OUT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    firm: Mapped["LawFirm"] = relationship("LawFirm", back_populates="lawyers")
    threads: Mapped[List["EmailThread"]] = relationship("EmailThread", back_populates="lawyer", cascade="all, delete-orphan")
    meetings: Mapped[List["Meeting"]] = relationship("Meeting", back_populates="lawyer", cascade="all, delete-orphan")


class EmailThread(Base):
    __tablename__ = "email_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lawyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("lawyers.id"), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="PENDING_APPROVAL")
    # PENDING_APPROVAL, SENT, REPLIED, IN_CONVERSATION, MEETING_BOOKED, CLOSED, OPTED_OUT
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    lawyer: Mapped["Lawyer"] = relationship("Lawyer", back_populates="threads")
    messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan", order_by="EmailMessage.sent_at")


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_threads.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20))  # OUTBOUND, INBOUND
    sender: Mapped[str] = mapped_column(String(255))
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="messages")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lawyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("lawyers.id"), index=True)
    thread_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("email_threads.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    scheduled_for: Mapped[str] = mapped_column(String(255))  # e.g. "Thursday, Oct 8 at 3:00 PM EAT"
    meeting_link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")  # CONFIRMED, COMPLETED, CANCELLED
    notified_founder: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    lawyer: Mapped["Lawyer"] = relationship("Lawyer", back_populates="meetings")


class OptOut(Base):
    __tablename__ = "opt_outs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unsubscribed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
