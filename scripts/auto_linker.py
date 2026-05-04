#!/usr/bin/env python3
"""
Auto-linker: injects contextual internal links into a new blog post.
Finds mentions of published post keywords in the post's HTML body,
inserts <a href> tags for the top 3 most relevant matches.

Usage: python scripts/auto_linker.py <slug>
Called automatically by generate_post.py after post creation.
"""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
KEYWORDS_FILE = ROOT / "scripts/keywords.json"
POSTS_DIR = ROOT / "blog/posts"
BLOG_URL = "https://blog.howmindswork.org"
MAX_LINKS = 3

def load_published_posts():
    data = json.loads(KEYWORDS_FILE.read_text())
    return [k for k in data["keywords"] if k.get("published") and k.get("post_title")]

def find_link_opportunities(html_body, published_posts, current_slug):
    soup = BeautifulSoup(html_body, "lxml")
    body_text = soup.get_text().lower()
    opportunities = []
    for post in published_posts:
        if post["slug"] == current_slug:
            continue
        keyword = post.get("keyword", "").lower().strip()
        title_lower = post.get("post_title", "").lower()
        match_text = keyword if keyword and keyword in body_text else None
        if not match_text:
            title_words = " ".join(title_lower.split()[:3])
            if len(title_words) > 8 and title_words in body_text:
                match_text = title_words
        if match_text:
            opportunities.append({**post, "match_text": match_text})
    return sorted(opportunities, key=lambda x: len(x["match_text"]), reverse=True)

def inject_links(html_body, published_posts, current_slug):
    opportunities = find_link_opportunities(html_body, published_posts, current_slug)[:MAX_LINKS]
    if not opportunities:
        return html_body

    soup = BeautifulSoup(html_body, "lxml")

    for opp in opportunities:
        match_text = opp["match_text"]
        href = f"{BLOG_URL}/posts/{opp['slug']}/"
        for p_tag in soup.find_all("p"):
            p_text = p_tag.get_text()
            if match_text.lower() not in p_text.lower():
                continue
            if p_tag.find("a"):
                continue
            pattern = re.compile(re.escape(match_text), re.IGNORECASE)
            new_html = pattern.sub(
                f'<a href="{href}">{match_text}</a>',
                str(p_tag),
                count=1,
            )
            p_tag.replace_with(BeautifulSoup(new_html, "lxml").find("p"))
            break

    return str(soup.find("article") or soup)

def link_post(slug):
    post_path = POSTS_DIR / slug / "index.html"
    if not post_path.exists():
        print(f"Post not found: {post_path}")
        return

    published = load_published_posts()
    html = post_path.read_text()

    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article", class_="post-body")
    if not article:
        print(f"No article.post-body found in {slug} — skipping")
        return

    original_article = str(article)
    linked_article = inject_links(original_article, published, slug)

    if linked_article == original_article:
        print(f"No link opportunities found for {slug}")
        return

    updated_html = html.replace(original_article, linked_article)
    post_path.write_text(updated_html)
    print(f"Injected internal links into {slug}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/auto_linker.py <slug>")
        sys.exit(1)
    link_post(sys.argv[1])
