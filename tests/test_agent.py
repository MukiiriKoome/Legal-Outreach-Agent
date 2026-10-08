import pytest
from src.agent.email_bot import LegalOutreachBot

def test_generate_initial_pitch():
    bot = LegalOutreachBot()
    pitch = bot.generate_initial_pitch(
        lawyer_name="Paras Shah",
        lawyer_title="Managing Partner",
        firm_name="Bowmans (Coulson Harney LLP)"
    )
    assert "Paras" in pitch["body"]
    assert "Bowmans" in pitch["body"]
    assert "Pre-Seed" in pitch["body"]
    assert "Calendly" in pitch["body"] or "calendly.com" in pitch["body"]

def test_intent_meeting_confirmation():
    bot = LegalOutreachBot()
    res = bot._rule_based_reply(
        first_name="Paras",
        firm_name="Bowmans",
        text="Hi Alex, this looks interesting. Let's meet this Thursday at 3 PM for a quick chat."
    )
    assert res["intent"] == "MEETING_CONFIRMED"
    assert res["is_meeting_detected"] is True
    assert "Thursday" in res["reply_body"]

def test_intent_asking_questions():
    bot = LegalOutreachBot()
    res = bot._rule_based_reply(
        first_name="Joyce",
        firm_name="Bowmans",
        text="Could you please send over your investor deck and tell me more about your traction in Kenya?"
    )
    assert res["intent"] == "ASKING_QUESTIONS"
    assert "indexed" in res["reply_body"].lower()

def test_intent_unsubscribe():
    bot = LegalOutreachBot()
    res = bot._rule_based_reply(
        first_name="John",
        firm_name="TripleOKLaw",
        text="Please unsubscribe me from this list immediately."
    )
    assert res["intent"] == "UNSUBSCRIBE"
