import httpx
from typing import Dict, Any, Optional
from src.config import settings

class FounderAlertManager:
    """
    Dispatches real-time alerts to the founder across Telegram, Slack, and email channels
    when an investor meeting is booked or critical action occurs.
    """

    @classmethod
    async def notify_meeting_booked(
        cls,
        lawyer_name: str,
        lawyer_title: str,
        firm_name: str,
        lawyer_email: str,
        meeting_time: str,
        meeting_link: str
    ) -> Dict[str, Any]:
        """
        Sends an urgent celebration / calendar alert across configured channels.
        """
        message_text = f"""🎉 **NEW INVESTOR MEETING BOOKED!** 🎉

👤 **Lawyer**: {lawyer_name} ({lawyer_title})
🏢 **Firm**: {firm_name} (Nairobi)
📧 **Email**: {lawyer_email}
🗓️ **Scheduled For**: {meeting_time}
🔗 **Meeting Link**: {meeting_link}

The AI chatbot successfully guided the lead to confirm a meeting.
"""
        results = {"console": True}

        # 1. Print formatted alert
        print(f"\n========================================================")
        print(message_text)
        print(f"========================================================\n")

        # 2. Telegram Alert
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            tg_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message_text,
                "parse_mode": "Markdown"
            }
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(tg_url, json=payload)
                    results["telegram"] = resp.status_code == 200
            except Exception as e:
                results["telegram_error"] = str(e)

        # 3. Slack Webhook Alert
        if settings.SLACK_WEBHOOK_URL:
            slack_payload = {
                "text": f"🎉 *New Investor Meeting Booked!*\n*{lawyer_name}* ({lawyer_title}) from *{firm_name}*\n*Time:* {meeting_time}\n*Link:* {meeting_link}"
            }
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(settings.SLACK_WEBHOOK_URL, json=slack_payload)
                    results["slack"] = resp.status_code == 200
            except Exception as e:
                results["slack_error"] = str(e)

        return results
