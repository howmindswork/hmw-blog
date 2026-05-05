import json
from pathlib import Path
from bs4 import BeautifulSoup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import optimizer

def make_soup(html):
    return BeautifulSoup(html, "lxml")

def test_has_schema_type_detects_faqpage():
    schema = json.dumps({"@type": "FAQPage", "mainEntity": []})
    soup = make_soup(f'<html><head><script type="application/ld+json">{schema}</script></head><body></body></html>')
    assert optimizer.has_schema_type(soup, "FAQPage") is True

def test_has_schema_type_returns_false_when_missing():
    soup = make_soup('<html><head></head><body></body></html>')
    assert optimizer.has_schema_type(soup, "FAQPage") is False

def test_check_date_modified_adds_field():
    schema = json.dumps({"@type": "BlogPosting", "headline": "Test"})
    html = f'<html><head><script type="application/ld+json">{schema}</script></head><body></body></html>'
    soup = make_soup(html)
    optimizer.fixes_made.clear()
    optimizer.check_date_modified(soup, "test-post")
    assert len(optimizer.fixes_made) == 1
    assert "dateModified" in optimizer.fixes_made[0]
