#!/usr/bin/env python3
"""Regenerate blog/index.html posts grid from keywords.json published entries."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

def load_published():
    kw = json.loads((ROOT / "scripts/keywords.json").read_text())
    return [k for k in kw["keywords"] if k.get("published") and k.get("post_title")]

def post_card_html(post):
    date_str = post.get("published_date", "")
    return f"""    <article class="post-card">
      <p class="post-date">{date_str}</p>
      <h2><a href="/blog/posts/{post['slug']}/">{post['post_title']}</a></h2>
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
