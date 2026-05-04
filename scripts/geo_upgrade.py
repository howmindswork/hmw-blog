#!/usr/bin/env python3
"""
One-time batch: upgrade GEO schema on all existing published posts.
Adds: dateModified, author.sameAs, Organization publisher, BreadcrumbList.
Safe to re-run — idempotent (checks before inserting).

Run: python scripts/geo_upgrade.py
"""
import json
import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent
KEYWORDS_FILE = ROOT / "scripts/keywords.json"
POSTS_DIR = ROOT / "blog/posts"
BLOG_URL = "https://blog.howmindswork.org"
AUTHOR_ID = "https://blog.howmindswork.org/about/#luke"
AUTHOR_SAME_AS = [
    "https://www.instagram.com/howmindswork/",
    "https://www.threads.net/@howmindswork",
    "https://www.tiktok.com/@howmindswork",
    "https://howmindswork.org",
]
TODAY = date.today().isoformat()

def upgrade_article_schema(schema_dict, published_date):
    schema_dict["dateModified"] = TODAY
    if "datePublished" not in schema_dict:
        schema_dict["datePublished"] = published_date
    author = schema_dict.get("author", {})
    if isinstance(author, dict):
        author["@type"] = "Person"
        author["name"] = "Luke Anthony"
        author["url"] = "https://howmindswork.org"
        author["sameAs"] = AUTHOR_SAME_AS
        schema_dict["author"] = author
    schema_dict["publisher"] = {
        "@type": "Organization",
        "name": "How Minds Work",
        "url": "https://howmindswork.org",
        "logo": {
            "@type": "ImageObject",
            "url": "https://blog.howmindswork.org/assets/og-default.jpg"
        }
    }
    if "image" not in schema_dict:
        schema_dict["image"] = f"{BLOG_URL}/assets/og-default.jpg"
    return schema_dict

def make_breadcrumb(url, title):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://howmindswork.org"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{BLOG_URL}/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": url},
        ]
    }

def upgrade_post(slug, published_date):
    post_path = POSTS_DIR / slug / "index.html"
    if not post_path.exists():
        print(f"  SKIP (not found): {slug}")
        return False

    html = post_path.read_text()
    post_url = f"{BLOG_URL}/posts/{slug}/"

    pattern = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.DOTALL)
    schemas = pattern.findall(html)
    has_breadcrumb = any('"BreadcrumbList"' in s[1] for s in schemas)

    new_html = html
    for open_tag, content, close_tag in schemas:
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            continue
        if obj.get("@type") in ("BlogPosting", "Article"):
            obj = upgrade_article_schema(obj, published_date)
            new_content = json.dumps(obj, indent=2)
            new_html = new_html.replace(
                open_tag + content + close_tag,
                open_tag + "\n" + new_content + "\n" + close_tag,
                1
            )

    if not has_breadcrumb:
        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1).replace(" — How Minds Work", "") if title_match else slug
        bc = json.dumps(make_breadcrumb(post_url, title), indent=2)
        bc_block = f'\n<script type="application/ld+json">\n{bc}\n</script>'
        new_html = new_html.replace("</head>", bc_block + "\n</head>", 1)

    if new_html != html:
        post_path.write_text(new_html)
        return True
    return False

def main():
    data = json.loads(KEYWORDS_FILE.read_text())
    published = [k for k in data["keywords"] if k.get("published")]
    print(f"Upgrading {len(published)} posts...")
    upgraded = 0
    for kw in published:
        result = upgrade_post(kw["slug"], kw.get("published_date", TODAY))
        status = "UPGRADED" if result else "SKIPPED"
        print(f"  {status}: {kw['slug']}")
        if result:
            upgraded += 1
    print(f"\nDone. {upgraded}/{len(published)} posts upgraded.")

if __name__ == "__main__":
    main()
