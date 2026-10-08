# Wakilify AI - Nairobi Legal Tech Investor Outreach Agent

An autonomous lead generation, web scraping, and conversational AI scheduling engine designed for Kenyan startup founders pitching to law firm partners and angel syndicates in Nairobi.

---

## 🏛️ System Overview

1. **Lead Scraping & Discovery**:
   - Curated directory and web crawlers targeting premier corporate law firms across Nairobi legal centers (Upper Hill, Westlands, Kilimani, Nairobi CBD).
   - Scrapes firm names, managing partners, practice areas, phone numbers, and work emails.
   - Built-in MX record DNS resolution, RFC email syntax validation, and opt-out registry checks.

2. **Personalized Cold Outreach**:
   - Generates bespoke, respectful pitch emails tailored to the recipient's firm and practice area.
   - Throttled delivery (with jitter delay) to protect mailbox reputation.
   - Full compliance with Kenya Data Protection Act 2019 (ODPC) and Advocates Act ethics (automatic opt-out handling and mandatory disclosures).
   - **Human-in-the-Loop Mode**: Review & approve pitches/replies via dashboard before sending.

3. **Multi-Turn AI Chatbot**:
   - Inbound email parsing with RFC threading (`In-Reply-To`, `References`).
   - Powered by Gemini 3.8 Flash (with intelligent rule-based / semantic fallback).
   - Classifies intent (`INTERESTED`, `ASKING_QUESTIONS`, `OBJECTION_TIME`, `OBJECTION_ETHICS`, `MEETING_CONFIRMED`, `UNSUBSCRIBE`).
   - Grounds answers in the startup's dossier, pilot traction, tech stack, and angel investment terms (SAFE notes, ticket sizes).

4. **Autonomous Meeting Booking & Founder Alerts**:
   - Detects when a partner proposes or confirms a meeting time.
   - Generates standard iCalendar (`.ics`) invites and Google Meet links.
   - Dispatches real-time celebratory alerts to the founder via **Telegram Bot**, **Slack Webhook**, or Email.

5. **Interactive Web Dashboard**:
   - Single Page Application with live stats, lead management, approval queue, active conversation thread viewer, meeting list, and a real-time **Inbound Reply Simulator**.

---

## 🚀 Quick Start

### 1. Prerequisites & Environment
```bash
cd /home/sama/.gemini/antigravity/scratch/legal-outreach-agent
source .venv/bin/activate
```

### 2. Configuration
Inspect or modify `.env`:
```env
STARTUP_NAME="Wakilify AI"
FOUNDER_NAME="Alex Mwangi"
FOUNDER_EMAIL="alex@wakilify.co.ke"
CALENDLY_URL="https://calendly.com/alex-wakilify/investor-coffee-15m"

# Email Mode: "mock" (safe testing) or "smtp" (live mail delivery)
EMAIL_MODE=mock

# Gemini API Key (optional - defaults to smart rule engine if unset)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash

# Notifications (Optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SLACK_WEBHOOK_URL=
```

---

## 💻 CLI Usage

### Seed Directory
Populate database with verified Nairobi law firms (Bowmans, ALN Kenya, TripleOKLaw, Kaplan & Stratton, Dentons, Igeria & Ngugi):
```bash
python cli.py seed
```

### List Leads
Display table of discovered advocates, firms, locations, and outreach statuses:
```bash
python cli.py list
```

### Preview or Dispatch Pitch
Draft initial outreach for a specific partner:
```bash
# Preview
python cli.py pitch --id 1

# Send (or queue if approval is required)
python cli.py pitch --id 1 --send
```

### Simulate Inbound Reply & Trigger Chatbot
Test how the AI handles inquiries or confirms meetings:
```bash
python cli.py simulate \
  --email paras.shah@bowmanslaw.com \
  --body "Hi Alex, this sounds promising. Let's meet this Thursday at 3 PM in Upper Hill to discuss."
```

### Launch Web Dashboard
```bash
python cli.py serve
```
Open your browser at `http://localhost:8000`.

---

## 🧪 Testing

Run the automated test suite (16 tests covering crawler, email verifier, AI agent, pipeline, and API):
```bash
pytest tests/
```

---

## 📁 Project Structure

```
legal-outreach-agent/
├── cli.py                     # Command-line interface
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
├── src/
│   ├── config.py              # Settings & environment parser
│   ├── database/
│   │   ├── db.py              # SQLite / DB session engine
│   │   └── models.py          # LawFirm, Lawyer, Thread, Message, Meeting, OptOut
│   ├── crawler/
│   │   ├── seed_data.py       # Curated Nairobi firm & partner directory
│   │   ├── firm_spider.py     # HTML crawler & scraper
│   │   └── contact_verifier.py# MX record validation & regex
│   ├── agent/
│   │   ├── knowledge_base.py  # Startup pitch dossier & objection playbooks
│   │   └── email_bot.py       # Gemini 3.8 Flash conversation agent
│   ├── email_service/
│   │   ├── sender.py          # Outbound mailer with throttling & headers
│   │   └── listener.py        # Inbound email processor & thread manager
│   ├── notifications/
│   │   ├── scheduler.py       # Calendar invite (.ics) & Google Meet creator
│   │   └── alert_manager.py   # Telegram / Slack / email founder alerts
│   └── web/
│       ├── app.py             # FastAPI REST endpoints
│       └── static/index.html  # Modern Tailwind CSS web dashboard
└── tests/
    ├── test_crawler.py
    ├── test_verifier.py
    ├── test_agent.py
    ├── test_pipeline.py
    └── test_api.py
```
