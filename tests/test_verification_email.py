import pytest
from app.services.verification_email import build_verification_email

def test_build_verification_email():
    name = "Test User"
    url = "http://example.com/verify"
    subject, body = build_verification_email(name, url)
    assert name in body
    assert url in body
    assert isinstance(subject, str)
    assert isinstance(body, str)
