import pytest
from src.crawler.contact_verifier import (
    is_valid_email_syntax,
    extract_first_name,
    verify_lead_email
)

def test_email_syntax_validation():
    assert is_valid_email_syntax("paras.shah@bowmanslaw.com") is True
    assert is_valid_email_syntax("dr.advocate+tech@tripleoklaw.co.ke") is True
    assert is_valid_email_syntax("invalid-email") is False
    assert is_valid_email_syntax("@missingusername.com") is False
    assert is_valid_email_syntax("name@domain") is False

def test_extract_first_name():
    assert extract_first_name("John M. Ohaga SC") == "John"
    assert extract_first_name("Adv. Arthur Igeria") == "Arthur"
    assert extract_first_name("Dr. Fred Ojiambo SC") == "Fred"
    assert extract_first_name("Paras Shah") == "Paras"

def test_verify_lead_email_basic():
    is_valid, msg = verify_lead_email("test.partner@bowmanslaw.com")
    assert is_valid is True
    assert "Valid" in msg

    is_invalid, msg_inv = verify_lead_email("not-an-email")
    assert is_invalid is False
