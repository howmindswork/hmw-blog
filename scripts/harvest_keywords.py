#!/usr/bin/env python3
"""
Daily keyword harvester: searches Exa for questions in HMW's 5 pillar topics,
deduplicates, appends up to 10 new entries to keywords.json.

Run: python scripts/harvest_keywords.py
GitHub Actions: .github/workflows/keyword-harvester.yml
"""
import json
import os
import re
import sys
import requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
KEYWORDS_FILE = ROOT / "scripts/keywords.json"
EXA_API_URL = "https://api.exa.ai/search"
MAX_NEW_PER_RUN = 10

PILLAR_QUERIES = [
    ("grief-rituals",        "grief ritual practices for healing loss"),
    ("somatic-healing",      "somatic exercises for grief and loss"),
    ("nervous-system",       "nervous system grief healing regulation"),
    ("emotional-completion", "how to complete unresolved grief emotionally"),
    ("breathwork",           "breathwork techniques for grief anxiety"),
]

PRODUCT_MAP = {
    "grief-rituals": {
        "product_name": "Stone Release Ritual",
        "product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
        "free_product_name": "Stone Release Ritual (free preview)",
        "free_product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
    },
    "somatic-healing": {
        "product_name": "Stone Release Ritual",
        "product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
        "free_product_name": "Stone Release Ritual (free preview)",
        "free_product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
    },
    "nervous-system": {
        "product_name": "Stone Release Ritual",
        "product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
        "free_product_name": "Stone Release Ritual (free preview)",
        "free_product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
    },
    "emotional-completion": {
        "product_name": "Emotional Completion Protocol",
        "product_url": "https://ritual.howmindswork.org/emotional-completion-protocol/",
        "free_product_name": "Stone Release Ritual (free preview)",
        "free_product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
    },
    "breathwork": {
        "product_name": "Stone Release Ritual",
        "product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
        "free_product_name": "Stone Release Ritual (free preview)",
        "free_product_url": "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio",
    },
}

def assign_product(pillar):
    return PRODUCT_MAP.get(pillar, PRODUCT_MAP["grief-rituals"])

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")

def format_keyword_entry(question, pillar):
    slug = slugify(question)
    product = assign_product(pillar)
    return {
        "slug": slug,
        "keyword": question.lower(),
        "pillar": pillar,
        "is_pillar": False,
        "phase": 1,
        "published": False,
        **product,
    }

def deduplicate(candidates, existing):
    existing_slugs = {e["slug"] for e in existing}
    existing_keywords = {e["keyword"].lower() for e in existing if e.get("keyword")}
    seen_slugs = set()
    result = []
    for c in candidates:
        c_keyword = c.get("keyword", "").lower()
        if (c["slug"] not in existing_slugs
                and (not c_keyword or c_keyword not in existing_keywords)
                and c["slug"] not in seen_slugs):
            result.append(c)
            seen_slugs.add(c["slug"])
    return result

def search_exa(query, pillar, api_key):
    try:
        resp = requests.post(
            EXA_API_URL,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={
                "query": query,
                "type": "neural",
                "numResults": 10,
                "contents": {"text": {"maxCharacters": 200}},
            },
            timeout=30,
        )
    except Exception as e:
        print(f"  Exa request failed for '{query}': {e}")
        return []

    if resp.status_code != 200:
        print(f"  Exa error {resp.status_code} for '{query}' — skipping")
        return []

    candidates = []
    for r in resp.json().get("results", []):
        title = r.get("title", "").strip()
        if not title or len(title) < 15 or len(title) > 120:
            continue
        if any(skip in title.lower() for skip in ["buy", "shop", "sale", "amazon", "reddit"]):
            continue
        candidates.append(format_keyword_entry(title, pillar))
    return candidates

def main():
    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        print("EXA_API_KEY not set — skipping harvest")
        sys.exit(0)

    data = json.loads(KEYWORDS_FILE.read_text())
    existing = data["keywords"]
    print(f"Existing keywords: {len(existing)}")

    all_candidates = []
    for pillar, query in PILLAR_QUERIES:
        print(f"  Searching: {query}")
        found = search_exa(query, pillar, api_key)
        all_candidates.extend(found)
        print(f"  Found {len(found)} candidates for {pillar}")

    new_entries = deduplicate(all_candidates, existing)[:MAX_NEW_PER_RUN]
    print(f"New unique keywords to add: {len(new_entries)}")

    if new_entries:
        data["keywords"].extend(new_entries)
        KEYWORDS_FILE.write_text(json.dumps(data, indent=2))
        print(f"keywords.json updated — total: {len(data['keywords'])}")
    else:
        print("No new keywords found this run")

if __name__ == "__main__":
    main()
