from src.config import settings

def get_startup_knowledge_base() -> str:
    """Returns the grounded knowledge base about the legal tech startup for the AI Agent."""
    return f"""
STARTUP DOSSIER & INVESTOR PROPOSITION
======================================
Company: {settings.STARTUP_NAME}
Founder: {settings.FOUNDER_NAME} ({settings.FOUNDER_EMAIL})
Tagline: {settings.STARTUP_TAGLINE}
Scheduling Link: {settings.CALENDLY_URL}

1. THE PROBLEM IN EAST AFRICA:
- African legal teams spend over 45% of billable hours on repetitive legal research, cross-referencing East African precedent (Kenya Law Reports, eKLR, Gazette notices), and manual contract diligence.
- Existing global tools (Harvey, Thomson Reuters CoCounsel) do not index local Common Law jurisprudence or understand local Kenyan statutory regimes (e.g. Kenya Data Protection Act 2019, Companies Act 2015, Land Act).

2. THE SOLUTION & TRACTION:
- {settings.STARTUP_NAME} is an AI-powered legal intelligence and contract review assistant built natively for Kenyan and East African corporate law firms.
- Traction: 8 pilot law firms in Nairobi (Upper Hill & Westlands), indexed 185,000+ Kenyan judgments, reducing contract audit and due diligence cycle times by 68%.
- Data Protection & Ethics: Designed to preserve advocate-client privilege with private cloud tenancy, local data sovereignty compliance (ODPC), and strict zero-training guarantees on client data.

3. ANGEL ROUND DETAILS:
- Round Size: ${settings.ROUND_TARGET_USD:,} Pre-Seed / Angel Round.
- Strategic Focus: Inviting select leading Nairobi advocates and partners as angel advisors and syndicate members to align industry expertise with technology.
- Minimum Check Size: ${settings.MIN_TICKET_USD:,} via standard Post-Money SAFE (Simple Agreement for Future Equity).

4. OBJECTION HANDLING GUIDELINES:
- Objection: "Is this legal in Kenya? Advocates cannot share fees with non-advocates."
  -> Response: Clarify that {settings.STARTUP_NAME} is enterprise software sold as a B2B SaaS tool directly to law firms and legal departments. It does not engage in unauthorized legal practice; it amplifies advocates.
- Objection: "What about client confidentiality?"
  -> Response: Enterprise security with end-to-end encryption, ISO 27001-compliant infrastructure, and strict non-retention agreements to protect advocate-client privilege.
- Objection: "I am too busy right now."
  -> Response: Respect their time. Propose a brief 10-15 minute introductory video chat or coffee in Westlands/Upper Hill at their convenience next week or offer to email our 2-page executive summary first.
- Objective: Always guide polite and interested lawyers toward booking an introductory 15-minute chat via {settings.CALENDLY_URL} or confirming a specific day/time.
"""
