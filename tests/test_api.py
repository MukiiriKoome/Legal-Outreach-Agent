import pytest
from fastapi.testclient import TestClient
from src.web.app import app
from src.database.db import init_db

client = TestClient(app)

def test_api_health_and_stats():
    init_db()
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_firms" in data
    assert "total_leads" in data
    assert "meetings_booked" in data

def test_api_leads_list():
    res = client.get("/api/leads")
    assert res.status_code == 200
    leads = res.json()
    assert isinstance(leads, list)
    assert len(leads) > 0

def test_api_threads():
    res = client.get("/api/threads")
    assert res.status_code == 200
    threads = res.json()
    assert isinstance(threads, list)

def test_api_meetings():
    res = client.get("/api/meetings")
    assert res.status_code == 200
    meetings = res.json()
    assert isinstance(meetings, list)

def test_api_settings():
    res = client.get("/api/settings")
    assert res.status_code == 200
    settings_data = res.json()
    assert "STARTUP_NAME" in settings_data
    assert "CALENDLY_URL" in settings_data

def test_dashboard_ui_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "Wakilify AI" in res.text
    assert "Nairobi Leads Pipeline" in res.text
