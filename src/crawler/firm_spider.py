import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.database.models import LawFirm, Lawyer
from src.crawler.seed_data import NAIROBI_LAW_FIRMS_SEED
from src.crawler.contact_verifier import verify_lead_email

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

class NairobiFirmSpider:
    """
    Crawler and parser for Nairobi law firm directories and practice websites.
    """

    def __init__(self, db: Session):
        self.db = db

    def seed_database(self) -> Dict[str, int]:
        """
        Populate the database with verified Nairobi law firms and partners from the curated directory.
        """
        firms_added = 0
        lawyers_added = 0

        for item in NAIROBI_LAW_FIRMS_SEED:
            firm = self.db.query(LawFirm).filter(LawFirm.name == item["firm_name"]).first()
            if not firm:
                firm = LawFirm(
                    name=item["firm_name"],
                    website=item.get("website"),
                    address=item.get("address"),
                    city=item.get("city", "Nairobi"),
                    practice_areas=item.get("practice_areas"),
                    source_url=item.get("website")
                )
                self.db.add(firm)
                self.db.flush()
                firms_added += 1

            for law_data in item.get("lawyers", []):
                email = law_data["email"].strip().lower()
                existing_lawyer = self.db.query(Lawyer).filter(Lawyer.email == email).first()
                if not existing_lawyer:
                    is_valid, _ = verify_lead_email(email, self.db)
                    lawyer = Lawyer(
                        firm_id=firm.id,
                        full_name=law_data["full_name"],
                        title=law_data.get("title", "Partner"),
                        email=email,
                        phone=law_data.get("phone"),
                        bio=law_data.get("bio"),
                        is_verified=is_valid,
                        status="VERIFIED" if is_valid else "NEW"
                    )
                    self.db.add(lawyer)
                    lawyers_added += 1

        self.db.commit()
        return {"firms_added": firms_added, "lawyers_added": lawyers_added}

    def scrape_custom_html(self, html_content: str, firm_name: str, firm_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses raw HTML of a law firm's team or people directory page,
        extracting lawyer profiles, emails, titles, and bios.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        extracted_lawyers = []

        # Find all mailto links or emails in text
        mailto_links = soup.find_all("a", href=re.compile(r"^mailto:", re.IGNORECASE))
        seen_emails = set()

        for link in mailto_links:
            raw_email = link.get("href", "").replace("mailto:", "").split("?")[0].strip().lower()
            if not raw_email or raw_email in seen_emails or not EMAIL_REGEX.match(raw_email):
                continue
            seen_emails.add(raw_email)

            # Attempt to find parent container for name and title
            parent = link.find_parent(["div", "section", "article", "li", "td"]) or link.parent
            text_block = parent.get_text(separator="\n", strip=True) if parent else link.get_text()

            lines = [line.strip() for line in text_block.split("\n") if line.strip()]
            name = lines[0] if lines else "Advocate / Partner"
            
            # Look for partner or lawyer title keywords
            title = "Partner"
            for line in lines:
                if any(k in line.lower() for k in ["partner", "managing partner", "director", "counsel", "associate", "advocate"]):
                    title = line
                    break

            extracted_lawyers.append({
                "full_name": name,
                "title": title,
                "email": raw_email,
                "firm_name": firm_name,
                "bio": text_block[:300] if len(text_block) > 300 else text_block
            })

        return extracted_lawyers

    async def crawl_firm_url(self, url: str, firm_name: str) -> List[Dict[str, Any]]:
        """
        Fetches a public website asynchronously and parses lawyer profiles.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return self.scrape_custom_html(resp.text, firm_name, url)
        except Exception as e:
            print(f"Crawler error fetching {url}: {e}")
        return []
