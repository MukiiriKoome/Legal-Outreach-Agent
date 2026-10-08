import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, LawFirm, Lawyer
from src.crawler.firm_spider import NairobiFirmSpider

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_scrape_custom_html(test_db):
    spider = NairobiFirmSpider(test_db)
    mock_html = """
    <div class="team-grid">
        <div class="lawyer-card">
            <h3>Sarah Kimani</h3>
            <p class="title">Managing Partner - Corporate & Tech</p>
            <p>Advise early stage startups and angel syndicates.</p>
            <a href="mailto:skimani@nairobilaw.co.ke">Email Sarah</a>
        </div>
        <div class="lawyer-card">
            <h3>David Ochieng</h3>
            <p class="title">Senior Associate</p>
            <a href="mailto:dochieng@nairobilaw.co.ke">Contact</a>
        </div>
    </div>
    """
    results = spider.scrape_custom_html(mock_html, "Nairobi Law LLP")
    assert len(results) == 2
    assert results[0]["email"] == "skimani@nairobilaw.co.ke"
    assert "Sarah Kimani" in results[0]["full_name"]
    assert "Managing Partner" in results[0]["title"]
    assert results[1]["email"] == "dochieng@nairobilaw.co.ke"

def test_seed_database(test_db):
    spider = NairobiFirmSpider(test_db)
    stats = spider.seed_database()
    assert stats["firms_added"] > 0
    assert stats["lawyers_added"] > 0

    firms = test_db.query(LawFirm).all()
    lawyers = test_db.query(Lawyer).all()
    assert len(firms) >= 5
    assert len(lawyers) >= 10
