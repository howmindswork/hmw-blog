#!/usr/bin/env python3
"""Regenerate blog/index.html posts grid from keywords.json published entries."""
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent

PILLAR_TO_FILTER = {
    "somatic-healing": "somatic",
    "emotional-completion": "completion",
    "how-to-feel-again": "numbness",
    "grief-rituals": "grief-ritual",
    "breathwork": "breathwork",
    "yoga-nidra": "yoga-nidra",
    "nsdr": "somatic",
}

def word_count_from_post(slug):
    post_file = ROOT / "blog/posts" / slug / "index.html"
    if not post_file.exists():
        return 0
    try:
        soup = BeautifulSoup(post_file.read_text(), "html.parser")
        body = soup.find(class_="post-body") or soup.find("main") or soup.body
        if not body:
            return 0
        return len(body.get_text().split())
    except Exception:
        return 0

def load_published():
    kw = json.loads((ROOT / "scripts/keywords.json").read_text())
    return [k for k in kw["keywords"] if k.get("published") and k.get("post_title")]

def post_card_html(post):
    date_str = post.get("published_date", "")
    pillar = post.get("pillar", "")
    cat = PILLAR_TO_FILTER.get(pillar, pillar.replace("-", " ") if pillar else "")
    words = word_count_from_post(post["slug"])
    mins = max(1, round(words / 200)) if words > 0 else "?"
    read_time = f"{mins} min read"
    return f"""    <article class="post-card" data-cat="{cat}">
      <p class="post-date">{date_str} <span class="read-time-static">{read_time}</span></p>
      <h2><a href="/posts/{post['slug']}/">{post['post_title']}</a></h2>
      <p class="post-excerpt">{post.get('meta_description', '')}</p>
    </article>"""

def render():
    posts = sorted(load_published(), key=lambda p: p.get("published_date",""), reverse=True)
    cards = "\n".join(post_card_html(p) for p in posts)
    index_path = ROOT / "blog/index.html"
    html = index_path.read_text()
    html = re.sub(
        r'(<div class="posts-grid" id="posts">).*?(</div>)',
        f'\\1\n{cards}\n  \\2',
        html, flags=re.DOTALL
    )
    index_path.write_text(html)
    print(f"Rendered {len(posts)} posts to blog/index.html")

if __name__ == "__main__":
    render()
