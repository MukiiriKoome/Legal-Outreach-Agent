import json
import re
from typing import Dict, Any, List, Optional
from src.config import settings
from src.agent.knowledge_base import get_startup_knowledge_base
from src.crawler.contact_verifier import extract_first_name

SYSTEM_INSTRUCTION = """You are an elite, highly professional AI Investment Outreach Assistant representing the founder of a high-growth legal tech startup in Nairobi, Kenya.

Your mission:
1. Conduct multi-turn email dialogues with senior Kenyan law firm partners and managing advocates.
2. Ground all answers strictly in the provided Startup Dossier.
3. Answer technical, legal, and financial questions diplomatically, respectfully observing Kenyan legal etiquette (addressing Senior Counsel and Partners respectfully).
4. Guide receptive lawyers towards scheduling a 15-minute introductory coffee or virtual meeting with the founder.
5. If a lawyer specifies a date and time to meet, confirm enthusiastically and note the meeting details.
6. If a lawyer asks to unsubscribe or is completely uninterested, be courteous and mark as opt-out.

Always return your assessment and draft reply in strict JSON format:
{
  "intent": "INTERESTED" | "ASKING_QUESTIONS" | "OBJECTION" | "MEETING_CONFIRMED" | "DECLINED" | "UNSUBSCRIBE",
  "sentiment": "POSITIVE" | "NEUTRAL" | "SKEPTICAL" | "NEGATIVE",
  "is_meeting_detected": true | false,
  "proposed_meeting_time": "e.g. Thursday Oct 8 at 3:00 PM EAT" or null,
  "reply_subject": "Re: ...",
  "reply_body": "Full body text formatted professionally without placeholders"
}
"""

class LegalOutreachBot:
    """
    Autonomous conversation agent powered by Gemini API with a robust rule-based fallback.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-3.8-flash"
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Gemini client: {e}")

    def generate_initial_pitch(self, lawyer_name: str, lawyer_title: str, firm_name: str) -> Dict[str, str]:
        """
        Generates the first cold outreach email tailored for a Nairobi law firm partner.
        """
        first_name = extract_first_name(lawyer_name)
        subject = f"Angel Advisory & Legal Tech Innovation | {settings.STARTUP_NAME} & {firm_name}"
        
        body = f"""Dear {first_name},

I hope this email finds you well.

I have followed your work and {firm_name}'s distinguished leadership in commercial and corporate practice in Nairobi. 

I am writing to you directly because we are building {settings.STARTUP_NAME} ({settings.STARTUP_TAGLINE}). Having piloted with corporate legal teams in Nairobi, we have indexed over 185,000 Kenyan judicial precedents and statutory regulations to reduce contract diligence and legal research cycles by nearly 70%.

We are currently opening a selective ${settings.ROUND_TARGET_USD:,} Pre-Seed Angel round. We are specifically looking to partner with visionary Kenyan advocates and law firm leaders as strategic angel advisors and syndicate investors (typical angel checks of ${settings.MIN_TICKET_USD:,} to $25k).

Given your deep experience at {firm_name}, I would be honored to share our 2-page brief and hear your perspective on the evolving legal tech landscape in East Africa.

Would you be open to a brief 15-minute introductory coffee in Westlands/Upper Hill, or a quick video call next week? 

You can pick a convenient slot here: {settings.CALENDLY_URL}

Kind regards,

{settings.FOUNDER_NAME}
Founder, {settings.STARTUP_NAME}
{settings.FOUNDER_EMAIL}
Nairobi, Kenya
"""
        return {"subject": subject, "body": body}

    def process_lawyer_reply(
        self,
        lawyer_name: str,
        lawyer_title: str,
        firm_name: str,
        thread_history: List[Dict[str, str]],
        latest_reply: str
    ) -> Dict[str, Any]:
        """
        Analyzes the inbound reply and drafts the next response.
        """
        first_name = extract_first_name(lawyer_name)

        # 1. Check if Gemini Client is active
        if self.client:
            try:
                knowledge_base = get_startup_knowledge_base()
                conversation_prompt = f"""
STARTUP DOSSIER:
{knowledge_base}

RECIPIENT INFO:
- Name: {lawyer_name} ({lawyer_title})
- Firm: {firm_name}

PREVIOUS THREAD MESSAGES:
{json.dumps(thread_history, indent=2)}

LATEST INBOUND LAWYER EMAIL:
\"\"\"{latest_reply}\"\"\"

Generate the analysis and response JSON strictly according to instructions.
"""
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=conversation_prompt,
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION,
                        "response_mime_type": "application/json"
                    }
                )
                if response.text:
                    parsed = json.loads(response.text)
                    return parsed
            except Exception as ex:
                print(f"Gemini API generation failed, falling back to rule-based engine: {ex}")

        # 2. Rule-Based Fallback Engine
        return self._rule_based_reply(first_name, firm_name, latest_reply)

    def _rule_based_reply(self, first_name: str, firm_name: str, text: str) -> Dict[str, Any]:
        """
        Sophisticated rule-based agent for sentiment, intent detection, and contextual reply.
        """
        lower = text.lower()

        # Unsubscribe detection
        if any(w in lower for w in ["unsubscribe", "remove me", "stop emailing", "cease and desist", "not authorized"]):
            return {
                "intent": "UNSUBSCRIBE",
                "sentiment": "NEGATIVE",
                "is_meeting_detected": False,
                "proposed_meeting_time": None,
                "reply_subject": "Unsubscribe Confirmation",
                "reply_body": f"Dear {first_name},\n\nUnderstood. You have been removed from our contact list immediately. We apologize for any inconvenience.\n\nBest regards,\n{settings.FOUNDER_NAME}"
            }

        # Meeting confirmation / scheduling detected
        time_match = re.search(r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week|\d{1,2}(?:st|nd|rd|th)?\s+(?:am|pm|at|\b))", lower)
        is_agreeing = any(w in lower for w in ["let's meet", "let's do", "sounds good", "available", "let's catch up", "happy to chat", "call me", "coffee", "zoom", "google meet", "calendar"])

        if is_agreeing or ("meet" in lower and time_match):
            detected_time = time_match.group(0).capitalize() if time_match else "your proposed time"
            return {
                "intent": "MEETING_CONFIRMED",
                "sentiment": "POSITIVE",
                "is_meeting_detected": True,
                "proposed_meeting_time": detected_time,
                "reply_subject": f"Meeting Confirmation: {settings.STARTUP_NAME} & {firm_name}",
                "reply_body": f"""Dear {first_name},

Thank you very much. I would be delighted to meet and discuss this further.

I have reserved time on our calendar for {detected_time}. I will send over a calendar invite with the Google Meet link, or we can coordinate in Westlands/Upper Hill if you prefer in-person.

If you would like to adjust the time, feel free to pick any slot directly on my calendar here:
{settings.CALENDLY_URL}

Looking forward to our conversation!

Warm regards,

{settings.FOUNDER_NAME}
Founder, {settings.STARTUP_NAME}
{settings.FOUNDER_EMAIL}
"""
            }

        # Inquiry on traction / deck / business model
        if any(w in lower for w in ["deck", "traction", "presentation", "financials", "revenue", "clients", "how does it work", "tell me more"]):
            return {
                "intent": "ASKING_QUESTIONS",
                "sentiment": "POSITIVE",
                "is_meeting_detected": False,
                "proposed_meeting_time": None,
                "reply_subject": f"Re: Legal Tech Innovation | {settings.STARTUP_NAME}",
                "reply_body": f"""Dear {first_name},

Thank you for your response and interest in {settings.STARTUP_NAME}.

To give you a quick snapshot:
- We have indexed over 185,000 East African decisions, statutes, and Kenya Gazette notices into a secure legal intelligence pipeline.
- Currently piloting with 8 commercial law firms in Nairobi, cutting contract diligence time by ~68%.
- Our round is a ${settings.ROUND_TARGET_USD:,} Pre-Seed round on a standard SAFE, with angel tickets from ${settings.MIN_TICKET_USD:,}.

I would love to walk you through a brief 10-minute live demonstration of the software and share our full investor memo.

Are you available for a brief call this week? You can pick any convenient 15-minute slot here:
{settings.CALENDLY_URL}

Best regards,

{settings.FOUNDER_NAME}
Founder, {settings.STARTUP_NAME}
"""
            }

        # Confidentiality / Legal Ethics objection
        if any(w in lower for w in ["privilege", "confidential", "security", "data protection", "odpc", "ethics", "advocates act"]):
            return {
                "intent": "OBJECTION",
                "sentiment": "NEUTRAL",
                "is_meeting_detected": False,
                "proposed_meeting_time": None,
                "reply_subject": f"Re: Client Privilege & Enterprise Security | {settings.STARTUP_NAME}",
                "reply_body": f"""Dear {first_name},

Thank you for raising this critical point. Advocate-client privilege and data confidentiality under the Kenya Data Protection Act 2019 are the core foundations of our architecture:

1. Zero Training Guarantee: No client documents or queries are ever used to train public models.
2. Tenant Isolation: Each law firm operates in an isolated private cloud tenancy with AES-256 encryption at rest and in transit.
3. Advocates Act Alignment: {settings.STARTUP_NAME} is an internal productivity tool for advocates, fully respecting the rule against sharing legal practice fees.

I would be glad to share our Security & Privilege Whitepaper and show you the platform in action. Would you have 15 minutes for a quick chat next week?
{settings.CALENDLY_URL}

Warm regards,

{settings.FOUNDER_NAME}
Founder, {settings.STARTUP_NAME}
"""
            }

        # Too busy / timing objection
        if any(w in lower for w in ["busy", "not right now", "next month", "traveling", "holiday", "tied up"]):
            return {
                "intent": "OBJECTION",
                "sentiment": "NEUTRAL",
                "is_meeting_detected": False,
                "proposed_meeting_time": None,
                "reply_subject": f"Re: {settings.STARTUP_NAME} - Following up later",
                "reply_body": f"""Dear {first_name},

I completely understand—you have a demanding schedule at {firm_name}.

May I follow up with you in a couple of weeks? In the meantime, I am happy to send our 2-page executive summary for your leisure reading.

Wishing you a productive week ahead.

Warm regards,

{settings.FOUNDER_NAME}
Founder, {settings.STARTUP_NAME}
"""
            }

        # Default general positive / engaging reply
        return {
            "intent": "INTERESTED",
            "sentiment": "POSITIVE",
            "is_meeting_detected": False,
            "proposed_meeting_time": None,
            "reply_subject": f"Re: Legal Tech Angel Advisory | {settings.STARTUP_NAME}",
            "reply_body": f"""Dear {first_name},

Thank you for your reply. We are very eager to share what we are building with the Nairobi legal community.

Would you be open to an introductory 15-minute coffee or virtual chat to discuss how strategic legal angels are participating in our Pre-Seed round?

You can reserve a time that suits your calendar here:
{settings.CALENDLY_URL}

Looking forward to connecting!

Best regards,

{settings.FOUNDER_NAME}
Founder, {settings.STARTUP_NAME}
"""
        }
