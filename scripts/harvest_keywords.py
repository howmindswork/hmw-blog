#!/usr/bin/env python3
"""
Daily keyword harvester - three sources:
  1. Exa neural search (requires EXA_API_KEY)
  2. pytrends - rising Google searches in HMW niches (no key needed)
  3. Reddit - top questions from grief/mental health subs (no key needed)

Deduplicates, appends up to 15 new entries to keywords.json.
Run: python scripts/harvest_keywords.py
GitHub Actions: .github/workflows/keyword-harvester.yml
"""
import json
import os
import re
import sys
import time
import requests
from pathlib import Path

ROOT = Path(__file__).parent.parent
KEYWORDS_FILE = ROOT / "scripts/keywords.json"
EXA_API_URL = "https://api.exa.ai/search"
MAX_NEW_PER_RUN = 15

PILLAR_QUERIES = [
    ("grief-rituals",        "grief ritual practices for healing loss"),
    ("somatic-healing",      "somatic exercises for grief and loss"),
    ("emotional-completion", "how to complete unresolved grief emotionally"),
    ("breathwork",           "breathwork techniques for grief anxiety"),
    ("how-to-feel-again",    "how to feel again after grief numbness"),
    ("yoga-nidra",           "yoga nidra for grief sleep healing"),
]

TRENDS_TOPICS = [
    ("grief-rituals",        "grief ritual"),
    ("somatic-healing",      "somatic healing"),
    ("emotional-completion", "emotional completion"),
    ("breathwork",           "breathwork grief"),
    ("how-to-feel-again",    "emotional numbness"),
    ("yoga-nidra",           "yoga nidra"),
]

REDDIT_SUBS = [
    ("r/grief",          "grief-rituals"),
    ("r/GriefSupport",   "grief-rituals"),
    ("r/mentalhealth",   "emotional-completion"),
    ("r/Meditation",     "yoga-nidra"),
    ("r/breathwork",     "breathwork"),
]

FREE_AUDIO_URL = "https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio"
FREE_AUDIO_NAME = "Star Feeding Ritual (free audio)"
WANTING_URL = "https://lukeisthere.gumroad.com/l/wanting"
WANTING_NAME = "The Wanting Signal (free)"

PRODUCT_MAP = {
    # Grief rituals → $27 step-by-step ritual guide (best match for ritual seekers)
    "grief-rituals": {
        "product_name": "Step-by-Step Grief Ritual Guide",
        "product_url": "https://lukeisthere.gumroad.com/l/EmotionalCompletionGuide",
        "free_product_name": FREE_AUDIO_NAME,
        "free_product_url": FREE_AUDIO_URL,
    },
    # Somatic → ECP ($37 premium) with Wanting Signal as free lead
    "somatic-healing": {
        "product_name": "Emotional Completion Protocol",
        "product_url": "https://ritual.howmindswork.org/emotional-completion-protocol/",
        "free_product_name": WANTING_NAME,
        "free_product_url": WANTING_URL,
    },
    # Emotional completion → ECP is the exact match
    "emotional-completion": {
        "product_name": "Emotional Completion Protocol",
        "product_url": "https://ritual.howmindswork.org/emotional-completion-protocol/",
        "free_product_name": FREE_AUDIO_NAME,
        "free_product_url": FREE_AUDIO_URL,
    },
    # Breathwork → Come Down ($27 - for exhausted high-functioning people)
    "breathwork": {
        "product_name": "The Permission to Stop",
        "product_url": "https://come-down.pages.dev",
        "free_product_name": FREE_AUDIO_NAME,
        "free_product_url": FREE_AUDIO_URL,
    },
    # How to feel again → Invisible Grief Companion + Wanting Signal free
    "how-to-feel-again": {
        "product_name": "The Invisible Grief Companion",
        "product_url": "https://invisible-grief-companion.pages.dev/",
        "free_product_name": WANTING_NAME,
        "free_product_url": WANTING_URL,
    },
    # Yoga Nidra → Star Feeding Ritual ($17) is literally a yoga nidra/NSDR product
    "yoga-nidra": {
        "product_name": "The Star Feeding Ritual",
        "product_url": "https://star-feeding-ritual.pages.dev",
        "free_product_name": FREE_AUDIO_NAME,
        "free_product_url": FREE_AUDIO_URL,
    },
    # NSDR → same as yoga nidra
    "nsdr": {
        "product_name": "The Star Feeding Ritual",
        "product_url": "https://star-feeding-ritual.pages.dev",
        "free_product_name": FREE_AUDIO_NAME,
        "free_product_url": FREE_AUDIO_URL,
    },
    # Grief rituals Celtic/ancestral → Grief Wave Playbook ($17)
    "ancestral-grief": {
        "product_name": "The Grief Wave Playbook",
        "product_url": "https://grief-wave-playbook.pages.dev",
        "free_product_name": FREE_AUDIO_NAME,
        "free_product_url": FREE_AUDIO_URL,
    },
    # Guilt/permission → Permission Letter page
    "guilt-grief": {
        "product_name": "You're Allowed to Laugh Again",
        "product_url": "https://permission-letter-healing-guilt.pages.dev",
        "free_product_name": WANTING_NAME,
        "free_product_url": WANTING_URL,
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
        "keyword": question.lower().strip("?").strip(),
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

def search_pytrends(topic_keyword, pillar):
    """Pull related rising queries from Google Trends via pytrends."""
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30))
        pt.build_payload([topic_keyword], cat=0, timeframe="now 7-d", geo="US")
        related = pt.related_queries()
        candidates = []
        for kw_type in ("rising", "top"):
            df = related.get(topic_keyword, {}).get(kw_type)
            if df is None or df.empty:
                continue
            for _, row in df.head(8).iterrows():
                q = str(row.get("query", "")).strip()
                if q and 15 <= len(q) <= 120:
                    candidates.append(format_keyword_entry(q, pillar))
        return candidates
    except Exception as e:
        print(f"  pytrends failed for '{topic_keyword}': {e}")
        return []

def search_reddit(subreddit, pillar):
    """Pull top question-titles from a subreddit (no auth needed)."""
    headers = {"User-Agent": "HMW-KeywordBot/1.0"}
    candidates = []
    for sort in ("hot", "top"):
        try:
            url = f"https://www.reddit.com/{subreddit}/{sort}.json?limit=25&t=week"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            posts = resp.json().get("data", {}).get("children", [])
            for p in posts:
                title = p.get("data", {}).get("title", "").strip()
                # Only keep question-style titles
                if not title or len(title) < 20 or len(title) > 120:
                    continue
                if not any(w in title.lower() for w in [
                    "how", "why", "what", "when", "does", "can", "is ", "help",
                    "feel", "grief", "loss", "heal", "numb", "ritual", "breath",
                ]):
                    continue
                if any(skip in title.lower() for skip in ["buy", "sale", "promo", "ad ", "[ad]"]):
                    continue
                candidates.append(format_keyword_entry(title, pillar))
        except Exception as e:
            print(f"  Reddit {subreddit}/{sort} failed: {e}")
        time.sleep(1)
    return candidates

def main():
    if not KEYWORDS_FILE.exists():
        data = {"keywords": []}
        KEYWORDS_FILE.write_text(json.dumps(data, indent=2))
    data = json.loads(KEYWORDS_FILE.read_text())
    existing = data["keywords"]
    print(f"Existing keywords: {len(existing)}")

    all_candidates = []

    # Source 1: Exa (if key set)
    api_key = os.environ.get("EXA_API_KEY", "")
    if api_key:
        print("\n[Exa]")
        for pillar, query in PILLAR_QUERIES:
            print(f"  Searching: {query}")
            found = search_exa(query, pillar, api_key)
            all_candidates.extend(found)
            print(f"  Found {len(found)} candidates")
    else:
        print("[Exa] EXA_API_KEY not set — skipping")

    # Source 2: Google Trends via pytrends
    print("\n[pytrends]")
    for topic_kw, pillar in TRENDS_TOPICS:
        print(f"  Trends: {topic_kw}")
        found = search_pytrends(topic_kw, pillar)
        all_candidates.extend(found)
        print(f"  Found {len(found)} candidates")
        time.sleep(2)  # be polite to Google

    # Source 3: Reddit questions
    print("\n[Reddit]")
    for subreddit, pillar in REDDIT_SUBS:
        print(f"  Reddit: {subreddit}")
        found = search_reddit(subreddit, pillar)
        all_candidates.extend(found)
        print(f"  Found {len(found)} candidates")

    new_entries = deduplicate(all_candidates, existing)[:MAX_NEW_PER_RUN]
    print(f"\nNew unique keywords to add: {len(new_entries)}")
    for e in new_entries:
        print(f"  - [{e['pillar']}] {e['keyword']}")

    if new_entries:
        data["keywords"].extend(new_entries)
        KEYWORDS_FILE.write_text(json.dumps(data, indent=2))
        print(f"keywords.json updated - total: {len(data['keywords'])}")
    else:
        print("No new keywords found this run")

if __name__ == "__main__":
    main()
