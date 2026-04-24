#!/usr/bin/env python3
"""
HMW Blog Post Generator
Picks next uncovered keyword → calls Claude API → renders HTML → updates sitemap
Run: python scripts/generate_post.py
GitHub Actions handles git commit/push after this script runs.
"""
import os, json, re, datetime, subprocess
from pathlib import Path
import anthropic
import requests

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "blog/posts"
KEYWORDS_FILE = SCRIPTS / "keywords.json"
BLOG_URL = "https://howmindswork.org/blog"
AUTHOR_ID = "https://howmindswork.org/blog/about/#luke"

POST_TOOL = {
    "name": "write_blog_post",
    "description": "Write a complete AEO/SEO-optimized blog post as structured data.",
    "input_schema": {
        "type": "object",
        "required": ["title", "meta_description", "intro", "key_takeaways", "sections", "faq"],
        "properties": {
            "title": {"type": "string"},
            "meta_description": {"type": "string"},
            "intro": {"type": "string"},
            "key_takeaways": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}},
            "sections": {
                "type": "array", "minItems": 4,
                "items": {
                    "type": "object",
                    "required": ["h2", "paragraphs"],
                    "properties": {
                        "h2": {"type": "string"},
                        "paragraphs": {"type": "array", "items": {"type": "string"}},
                        "cta_type": {"type": "string", "enum": ["none", "inline_free", "inline_paid"]}
                    }
                }
            },
            "faq": {
                "type": "array", "minItems": 4, "maxItems": 6,
                "items": {
                    "type": "object",
                    "required": ["question", "answer"],
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"}
                    }
                }
            }
        }
    }
}

SYSTEM_PROMPT = """You write blog posts for How Minds Work (howmindswork.org), a personal brand by Luke focused on emotional healing, grief processing, somatic rituals, and emotional completion.

Luke's framework is called The Emotional Completion Ritual. His signature products:
- Stone Release Ritual (audio) — somatic grief release
- The Wanting Protocol — healing emotional numbness, feeling desire again
- Emotional Completion Guide — completing grief
- Caoineadh Anama — Irish ancestral grief protocol

VOICE: Direct, peer-level, initiating. "Here's exactly what to do." Not clinical. Not a therapist talking at you. The reader is an adult who can handle real information. Write like a knowledgeable friend who has been through this.

RULES:
- H2 headings must be questions (not statements)
- Every 3-4 paragraphs, include a specific cited statistic or research finding
- Include at least one named, step-by-step practice or protocol in the post body
- Reference The Emotional Completion Ritual methodology where it fits naturally
- Paragraphs max 100 words. One claim per paragraph.
- Total body length: 1,500-2,000 words across all sections combined
- Do not use urgency language or fake scarcity in CTAs
- CTA copy style: "Whenever you're ready" / "Start here if you're ready" / "For anyone carrying this alone"
- Title must be the keyword phrased as a question or clear statement (max 65 chars)
- Meta description: 155 chars max, includes keyword + emotional hook
- intro: 40-60 words, direct answer, no preamble
- First CTA (inline_free) goes in section at index 1 (after second section)
- Second CTA (inline_paid) goes in section at index 3 (after fourth section)
- All other sections: cta_type "none"
"""

def load_keywords():
    return json.loads(KEYWORDS_FILE.read_text())

def save_keywords(data):
    KEYWORDS_FILE.write_text(json.dumps(data, indent=2))

def next_keyword(data):
    for kw in data["keywords"]:
        if not kw.get("published"):
            return kw
    return None

def generate_post(kw):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_msg = f"""Write a blog post targeting this keyword: "{kw['keyword']}"

Free CTA product: {kw['free_product_name']} → {kw['free_product_url']}
Paid CTA product: {kw['product_name']} → {kw['product_url']}

Set cta_type "inline_free" on section index 1, "inline_paid" on section index 3, "none" on all others."""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[POST_TOOL],
        tool_choice={"type": "tool", "name": "write_blog_post"},
        messages=[{"role": "user", "content": user_msg}]
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "write_blog_post":
            return block.input
    raise ValueError("No tool_use block in response")

def paragraphs_html(paras):
    return "\n".join(f"<p>{p}</p>" for p in paras)

def cta_html(cta_type, kw):
    if cta_type == "inline_free":
        return f"""<div class="cta-block">
  <p class="cta-label">Start Here</p>
  <h3>Whenever you're ready — begin with this</h3>
  <p>A free audio guide to get you started with somatic grief release. No commitment, no pressure.</p>
  <a href="{kw['free_product_url']}" class="btn-primary">Get the free audio</a>
</div>"""
    if cta_type == "inline_paid":
        return f"""<div class="cta-block">
  <p class="cta-label">Go Deeper</p>
  <h3>Ready to go further?</h3>
  <p>For anyone who's been carrying this alone — {kw['product_name']} was built for exactly this.</p>
  <a href="{kw['product_url']}" class="btn-primary">Explore {kw['product_name']}</a>
</div>"""
    return ""

def sections_html(sections, kw):
    out = []
    for s in sections:
        out.append(f"<h2>{s['h2']}</h2>")
        out.append(paragraphs_html(s["paragraphs"]))
        cta = cta_html(s.get("cta_type", "none"), kw)
        if cta:
            out.append(cta)
    return "\n\n".join(out)

def faq_html(faq):
    items = "\n".join(
        f'<div class="faq-item"><h3>{f["question"]}</h3><p>{f["answer"]}</p></div>'
        for f in faq
    )
    return f'<section class="faq"><h2>Frequently Asked Questions</h2>{items}</section>'

def faq_schema(faq):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}
            } for f in faq
        ]
    }

def article_schema(post, kw, url, date_iso):
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"],
        "description": post["meta_description"],
        "url": url,
        "datePublished": date_iso,
        "dateModified": date_iso,
        "author": {"@id": AUTHOR_ID},
        "publisher": {
            "@type": "Person",
            "name": "Luke",
            "url": "https://howmindswork.org/blog/about/"
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url}
    }

def render_html(post, kw, date_str, date_iso, post_url):
    takeaways_li = "\n".join(f"<li>{t}</li>" for t in post["key_takeaways"])
    body_content = sections_html(post["sections"], kw)
    faq_content = faq_html(post["faq"])
    a_schema = json.dumps(article_schema(post, kw, post_url, date_iso), indent=2)
    f_schema = json.dumps(faq_schema(post["faq"]), indent=2)

    title_escaped = post['title'].replace('"', '&quot;').replace("'", "&#39;")
    meta_escaped = post['meta_description'].replace('"', '&quot;').replace("'", "&#39;")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{post['title']} — How Minds Work</title>
<meta name="description" content="{meta_escaped}">
<meta property="og:title" content="{title_escaped}">
<meta property="og:description" content="{meta_escaped}">
<meta property="og:type" content="article">
<meta property="og:url" content="{post_url}">
<meta property="og:image" content="{BLOG_URL}/assets/og-default.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{post_url}">
<link rel="stylesheet" href="/blog/assets/style.css">
<script type="application/ld+json">
{a_schema}
</script>
<script type="application/ld+json">
{f_schema}
</script>
</head>
<body>
<nav><div class="container">
  <a href="https://howmindswork.org" class="nav-brand">How Minds Work</a>
  <a href="/blog/" style="font-size:0.85rem;color:var(--text-muted)">← All posts</a>
</div></nav>

<header class="post-header"><div class="container">
  <div class="post-meta">
    <span>{date_str}</span>
    <span>·</span>
    <a href="/blog/about/">By Luke</a>
  </div>
  <h1>{post['title']}</h1>
</div></header>

<main><div class="container">
<article class="post-body">

<div class="disclaimer">
  <strong>Note:</strong> This content is not a substitute for professional therapy or medical care. If you are in crisis, please reach out to a mental health professional.
</div>

<p><strong>{post['intro']}</strong></p>

<div class="takeaways">
  <h3>Key Takeaways</h3>
  <ul>{takeaways_li}</ul>
</div>

{body_content}

{faq_content}

<div class="cta-block">
  <p class="cta-label">What's Next</p>
  <h3>Start whenever you're ready</h3>
  <p>For anyone who's been carrying this alone — these tools were built for exactly this.</p>
  <a href="{kw['free_product_url']}" class="btn-primary">Get the free audio</a>
  <a href="{kw['product_url']}" class="btn-secondary">{kw['product_name']} →</a>
</div>

<div class="author-card">
  <img src="/blog/assets/og-default.jpg" alt="Luke">
  <div>
    <p class="author-name">Luke</p>
    <p class="author-bio">Creator of The Emotional Completion Ritual. Writes about grief processing, somatic healing, and emotional completion at How Minds Work. <a href="/blog/about/">About Luke →</a></p>
  </div>
</div>

</article>
</div></main>

<footer><div class="container">
  <span>© 2026 How Minds Work</span>
  <span><a href="/blog/">Blog</a> · <a href="https://howmindswork.org">Products</a> · <a href="/blog/about/">About</a></span>
</div></footer>
</body>
</html>"""

def update_sitemap(slugs):
    today = datetime.date.today().isoformat()
    urls = [f"""  <url>
    <loc>{BLOG_URL}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""]
    for slug in slugs:
        urls.append(f"""  <url>
    <loc>{BLOG_URL}/posts/{slug}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    (ROOT / "blog/sitemap.xml").write_text(xml)
    print(f"Sitemap updated with {len(slugs)} posts")

def submit_to_bing(url):
    key = os.environ.get("BING_WEBMASTER_KEY")
    if not key:
        print("BING_WEBMASTER_KEY not set — skipping Bing submission")
        return
    resp = requests.post(
        "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl",
        params={"apikey": key},
        json={"siteUrl": "https://howmindswork.org", "url": url},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    print(f"Bing submission: {resp.status_code} — {url}")

def main():
    data = load_keywords()
    kw = next_keyword(data)
    if not kw:
        print("All keywords published. Add more to keywords.json.")
        return

    print(f"Generating post for: {kw['keyword']}")
    post = generate_post(kw)

    today = datetime.date.today()
    date_str = today.strftime("%B %d, %Y")
    date_iso = today.isoformat()
    post_url = f"{BLOG_URL}/posts/{kw['slug']}/"

    post_dir = POSTS_DIR / kw["slug"]
    post_dir.mkdir(parents=True, exist_ok=True)
    html = render_html(post, kw, date_str, date_iso, post_url)
    (post_dir / "index.html").write_text(html)
    print(f"Written: blog/posts/{kw['slug']}/index.html")

    for entry in data["keywords"]:
        if entry["slug"] == kw["slug"]:
            entry["published"] = True
            entry["published_date"] = date_iso
            entry["post_title"] = post["title"]
            entry["meta_description"] = post["meta_description"]
    save_keywords(data)

    subprocess.run(["python3", str(SCRIPTS / "render_index.py")], check=True)

    published_slugs = [k["slug"] for k in data["keywords"] if k.get("published")]
    update_sitemap(published_slugs)

    submit_to_bing(post_url)

if __name__ == "__main__":
    main()
