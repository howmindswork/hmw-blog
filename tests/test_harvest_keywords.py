import json, sys
from pathlib import Path
sys.path.insert(0, '/home/luke/hmw-blog')
from scripts.harvest_keywords import format_keyword_entry, deduplicate, assign_product

def test_format_keyword_entry():
    entry = format_keyword_entry("Why do I feel nothing after losing someone?", "emotional-completion")
    assert entry["slug"] == "why-do-i-feel-nothing-after-losing-someone"
    assert entry["pillar"] == "emotional-completion"
    assert entry["published"] == False
    assert "product_url" in entry
    assert "free_product_url" in entry

def test_deduplicate_removes_existing():
    existing = [{"slug": "somatic-healing-after-loss"}, {"slug": "breathwork-for-grief"}]
    candidates = [
        {"slug": "somatic-healing-after-loss"},
        {"slug": "vagal-toning-for-grief"},
    ]
    result = deduplicate(candidates, existing)
    assert len(result) == 1
    assert result[0]["slug"] == "vagal-toning-for-grief"

def test_assign_product_grief_rituals():
    product = assign_product("grief-rituals")
    assert "product_name" in product
    assert "product_url" in product
    assert "free_product_name" in product
