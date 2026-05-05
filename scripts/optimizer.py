#!/usr/bin/env python3
"""Weekly SEO optimizer — scans posts, auto-fixes safe issues, writes revenue leak report."""

import os
import json
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup

BLOG_DIR = Path(__file__).parent.parent / "blog"
POSTS_DIR = BLOG_DIR / "posts"
REPORT_FILE = BLOG_DIR / "optimizer-report.md"
ANALYTICS_ENDPOINT = os.environ.get("ANALYTICS_URL", "")

# ── Auto-fix tracking ────────────────────────────────────────────────────────
fixes_made = []
flags = []

def log_fix(slug, what):
    fixes_made.append(f"- `{slug}`: {what}")
    print(f"  FIX [{slug}] {what}")

def log_flag(slug, what):
    flags.append(f"- `{slug}`: {what}")
    print(f"  FLAG [{slug}] {what}")

# ── Schema helpers ───────────────────────────────────────────────────────────
def has_schema_type(soup, schema_type):
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = [data] if isinstance(data, dict) else data
        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == schema_type:
                return True
    return False

def get_article_schema(soup):
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = [data] if isinstance(data, dict) else data
        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]
        for item in items:
            if isinstance(item, dict) and item.get("@type") in ("BlogPosting", "Article"):
                return item, tag
    return None, None

# ── Individual checks ────────────────────────────────────────────────────────
def check_faq_schema(soup, slug):
    if not has_schema_type(soup, "FAQPage"):
        log_flag(slug, "missing FAQPage schema — add 4 Q&A pairs")

def check_date_modified(soup, slug):
    article, tag = get_article_schema(soup)
    if article and not article.get("dateModified"):
        # Auto-fix: add dateModified = today
        article["dateModified"] = date.today().isoformat()
        tag.string = json.dumps(article, indent=2)
        log_fix(slug, f"added dateModified = {date.today().isoformat()}")

def check_breadcrumb(soup, slug, post_url):
    if not has_schema_type(soup, "BreadcrumbList"):
        # Auto-fix: add breadcrumb before </head>
        breadcrumb = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://blog.howmindswork.org/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://blog.howmindswork.org/posts/"},
                {"@type": "ListItem", "position": 3, "name": soup.title.string if soup.title else slug, "item": post_url}
            ]
        }
        new_tag = soup.new_tag("script", type="application/ld+json")
        new_tag.string = json.dumps(breadcrumb, indent=2)
        head = soup.find("head")
        if head:
            head.append(new_tag)
            log_fix(slug, "added BreadcrumbList schema")

def check_cta(soup, slug):
    body_el = soup.find(class_="post-body") or soup.find("article") or soup.find("main")
    if not body_el:
        return
    links = body_el.find_all("a", href=True)
    has_cta = any("gumroad" in (a["href"] or "") or "stripe.com" in (a["href"] or "") or "howmindswork.org" in (a["href"] or "") for a in links)
    if not has_cta:
        # Auto-fix: append a minimal CTA block
        cta_html = '''<div class="cta-block" style="margin:2rem 0;padding:1.5rem;border:1px solid rgba(167,139,250,0.3);border-radius:8px;text-align:center;background:rgba(124,58,237,0.05);">
<p style="margin-bottom:1rem;font-style:italic;">Ready to go deeper into this work?</p>
<a href="https://howmindswork.org" style="display:inline-block;background:#7c3aed;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600;">Explore the Healing Rituals →</a>
</div>'''
        body_el.append(BeautifulSoup(cta_html, "html.parser"))
        log_fix(slug, "added missing CTA block")

def check_broken_links(soup, slug):
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/posts/"):
            post_slug = href.strip("/").split("/")[-1] if href.strip("/") else ""
            target = POSTS_DIR / post_slug / "index.html"
            if post_slug and not target.exists():
                # Auto-fix: remove the href but keep the text
                del a["href"]
                a["data-broken-link"] = href
                log_fix(slug, f"removed broken internal link: {href}")

def check_sitemap(slug, post_html_file):
    sitemap_path = BLOG_DIR / "sitemap.xml"
    if not sitemap_path.exists():
        return
    sitemap = sitemap_path.read_text()
    post_url = f"https://blog.howmindswork.org/posts/{slug}/"
    if post_url not in sitemap:
        log_flag(slug, "post URL missing from sitemap.xml — run render_index.py")

# ── Main scanner ─────────────────────────────────────────────────────────────
def scan_posts():
    if not POSTS_DIR.exists():
        print(f"Posts dir not found: {POSTS_DIR}")
        return

    html_files = sorted(POSTS_DIR.glob("*/index.html"))
    print(f"Scanning {len(html_files)} posts...")

    for html_file in html_files:
        slug = html_file.parent.name
        print(f"  Checking: {slug}")
        content = html_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "lxml")

        post_url = f"https://blog.howmindswork.org/posts/{slug}"
        check_date_modified(soup, slug)
        check_breadcrumb(soup, slug, post_url)
        check_cta(soup, slug)
        check_broken_links(soup, slug)
        check_faq_schema(soup, slug)
        check_sitemap(slug, html_file)

        # Write back fixed HTML
        html_file.write_text(str(soup), encoding="utf-8")

# ── Report writer ─────────────────────────────────────────────────────────────
def write_report():
    today = date.today().isoformat()
    lines = [
        f"# SEO Optimizer Report — {today}\n",
        f"Generated by scripts/optimizer.py\n\n",
        f"## Auto-Fixed ({len(fixes_made)} issues)\n",
    ]
    if fixes_made:
        lines.extend(fixes_made)
    else:
        lines.append("- No issues found.\n")

    lines.extend([
        f"\n## Flagged for Review ({len(flags)} items)\n",
    ])
    if flags:
        lines.extend(flags)
    else:
        lines.append("- Nothing to review.\n")

    lines.extend([
        "\n## Notes\n",
        "- Posts with high impressions but low CTR: check Google Search Console\n",
        "- Posts with >200 views and 0 CTA clicks: check analytics worker /report endpoint\n",
        f"- Analytics endpoint: {ANALYTICS_ENDPOINT or 'not configured (set ANALYTICS_URL secret)'}\n",
    ])

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_FILE}")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"HMW SEO Optimizer — {date.today().isoformat()}")
    scan_posts()
    write_report()
    print(f"\nDone. {len(fixes_made)} fixes, {len(flags)} flags.")
    if fixes_made:
        print("Auto-fixes applied — commit and deploy to push changes.")
