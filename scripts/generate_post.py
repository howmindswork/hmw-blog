#!/usr/bin/env python3
"""
HMW Blog Post Generator
Picks next uncovered keyword → calls Claude API → renders HTML → updates sitemap
Run: python scripts/generate_post.py
GitHub Actions handles git commit/push after this script runs.
"""
import os, json, re, datetime, subprocess, time, textwrap
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "llama-3.3-70b"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODEL = "gemini-2.5-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"

def _build_providers():
    providers = []
    # Cerebras first — fastest inference available, free tier
    k = os.environ.get("CEREBRAS_API_KEY", "")
    if k:
        providers.append(("cerebras", CEREBRAS_URL, k, CEREBRAS_MODEL))
    # All Groq keys — rotate through all before giving up
    groq_env_names = [
        "GROQ_API_KEY",
        "GROQ_API_KEY_2","GROQ_API_KEY_3","GROQ_API_KEY_4",
        "GROQ_API_KEY_5","GROQ_API_KEY_6","GROQ_API_KEY_7","GROQ_API_KEY_8",
        "GROQ_API_KEY_NEW_1","GROQ_API_KEY_NEW_2","GROQ_API_KEY_NEW_3",
        "GROQ_API_KEY_NEW_4","GROQ_API_KEY_NEW_5","GROQ_API_KEY_NEW_6","GROQ_API_KEY_NEW_7",
    ]
    for env in groq_env_names:
        k = os.environ.get(env, "")
        if k:
            providers.append(("groq", GROQ_URL, k, GROQ_MODEL))
    # Gemini fallbacks
    for env in ("GEMINI_API_KEY_BLOG", "GEMINI_API_KEY"):
        k = os.environ.get(env, "")
        if k:
            providers.append(("gemini", GEMINI_URL, k, GEMINI_MODEL))
    # OpenRouter last resort
    k = os.environ.get("OPENROUTER_API_KEY", "")
    if k:
        providers.append(("openrouter", OPENROUTER_URL, k, OPENROUTER_MODEL))
    return providers

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "blog/posts"
KEYWORDS_FILE = SCRIPTS / "keywords.json"
OG_ASSETS_DIR = ROOT / "blog/assets/posts"
_FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
_OG_W, _OG_H = 1200, 630


def make_og(title, slug):
    """Generate a branded 1200x630 WebP OG image for a blog post."""
    OG_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out = OG_ASSETS_DIR / f"{slug}-og.webp"
    img = Image.new("RGB", (_OG_W, _OG_H), color=(8, 7, 6))
    draw = ImageDraw.Draw(img)
    # Purple glow top-right
    glow = Image.new("RGB", (_OG_W, _OG_H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(400, 0, -1):
        alpha = int(80 * (1 - r / 400))
        gd.ellipse([(_OG_W - r, -r // 2), (_OG_W + r // 2, r)], fill=(alpha * 2, 0, alpha * 3))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = Image.blend(img, glow, 0.9)
    draw = ImageDraw.Draw(img)
    font_brand = ImageFont.truetype(_FONT_DIR + "DejaVuSerif.ttf", 24)
    font_title = ImageFont.truetype(_FONT_DIR + "DejaVuSerif-Bold.ttf", 68)
    font_name  = ImageFont.truetype(_FONT_DIR + "DejaVuSerif.ttf", 22)
    font_wm    = ImageFont.truetype(_FONT_DIR + "DejaVuSans.ttf", 18)
    # Gold rule + brand
    draw.rectangle([(60, 58), (400, 62)], fill=(212, 175, 55))
    draw.text((60, 80), "HOW MINDS WORK", font=font_brand, fill=(212, 175, 55))
    # Title (max 3 lines, wrap at 30 chars)
    lines = textwrap.wrap(title, width=30)[:3]
    y = 190
    for line in lines:
        draw.text((60, y), line, font=font_title, fill=(255, 255, 255))
        y += 82
    # Category label
    draw.text((60, y + 12), "Grief Healing Guide", font=font_name, fill=(212, 175, 55))
    # Bottom divider + author
    draw.rectangle([(60, _OG_H - 110), (_OG_W - 60, _OG_H - 108)], fill=(80, 60, 20))
    draw.text((60, _OG_H - 85), "Luke Anthony  ·  howmindswork.org", font=font_name, fill=(180, 155, 90))
    # Watermark bottom-right
    wm = "blog.howmindswork.org"
    bbox = draw.textbbox((0, 0), wm, font=font_wm)
    wx = _OG_W - (bbox[2] - bbox[0]) - 20
    wy = _OG_H - (bbox[3] - bbox[1]) - 15
    draw.text((wx + 1, wy + 1), wm, font=font_wm, fill=(0, 0, 0))
    draw.text((wx, wy), wm, font=font_wm, fill=(180, 180, 180))
    img.save(out, "WEBP", quality=85)
    print(f"OG image: {out.name}")

# Load pillar map once at module level; silently skip if missing
def _load_pillar_map():
    _path = SCRIPTS / "pillar_map.json"
    try:
        return json.loads(_path.read_text())
    except Exception:
        return {}

PILLAR_MAP = _load_pillar_map()
BLOG_URL = "https://blog.howmindswork.org"
AUTHOR_ID = "https://blog.howmindswork.org/about/#luke"
AUTHOR_SAME_AS = [
    "https://www.instagram.com/howmindswork/",
    "https://www.threads.net/@howmindswork",
    "https://www.tiktok.com/@howmindswork",
    "https://howmindswork.org",
]


SYSTEM_PROMPT = """You write blog posts for How Minds Work (howmindswork.org), a personal brand by Luke focused on emotional healing, grief processing, somatic rituals, and emotional completion.

Luke's framework is called The Emotional Completion Ritual. His signature products:
- Stone Release Ritual (audio): somatic grief release
- The Wanting Protocol: healing emotional numbness, feeling desire again
- Emotional Completion Guide: completing grief
- Caoineadh Anama: Irish ancestral grief protocol

VOICE: Direct, peer-level, initiating. "Here's exactly what to do." Not clinical. Not a therapist talking at you. The reader is an adult who can handle real information. Write like a knowledgeable friend who has been through this.

ABSOLUTE RULES — NO EXCEPTIONS:
- NEVER use em dashes (—). This is an absolute rule. Rewrite the sentence instead. Use a period, comma, or colon. Never reach for an em dash.
- NEVER use these words: delve, journey, moreover, furthermore, additionally, it's important to note, in conclusion, comprehensive, robust, nuanced, realm, tapestry, navigate, foster, leverage, underscore, holistic
- Write short sentences. Max 20 words per sentence. If a sentence runs long, split it.
- No filler phrases. No throat-clearing introductions. Start with the point.

WRITING STYLE — sound human, not AI:
- Use contractions (you're, it's, don't, you've)
- Never start paragraphs with: Moreover, Furthermore, Additionally, It's worth noting, In conclusion, Ultimately
- Vary sentence openings. Don't repeat the same structure twice in a row.
- Specific over vague. "Three days after the funeral" not "in the aftermath of loss."
- One idea per sentence when the idea is hard. Split it.

RULES:
- H2 headings must be questions (not statements)
- Every 3-4 paragraphs, include a specific cited statistic or research finding with source name
- Include at least one named, step-by-step practice or protocol with numbered steps
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
    providers = _build_providers()
    if not providers:
        raise ValueError("No API keys configured — set GROQ_API_KEY or GEMINI_API_KEY")
    provider_idx = 0
    api_url, api_key, model = providers[0][1], providers[0][2], providers[0][3]

    user_msg = f"""Write a blog post targeting this keyword: "{kw['keyword']}"

Free CTA product: {kw['free_product_name']} — URL: {kw['free_product_url']}
Paid CTA product: {kw['product_name']} — URL: {kw['product_url']}

Set cta_type "inline_free" on section index 1, "inline_paid" on section index 3, "none" on all others.

Respond with ONLY a valid JSON object matching this exact structure (no markdown, no code blocks, just raw JSON):
{{
  "title": "string (max 65 chars)",
  "meta_description": "string (max 155 chars)",
  "intro": "string (40-60 words)",
  "key_takeaways": ["string", "string", "string"],
  "sections": [
    {{"h2": "string", "paragraphs": ["string"], "cta_type": "none"}},
    {{"h2": "string", "paragraphs": ["string"], "cta_type": "inline_free"}},
    {{"h2": "string", "paragraphs": ["string"], "cta_type": "none"}},
    {{"h2": "string", "paragraphs": ["string"], "cta_type": "inline_paid"}},
    {{"h2": "string", "paragraphs": ["string"], "cta_type": "none"}}
  ],
  "faq": [
    {{"question": "string", "answer": "string"}},
    {{"question": "string", "answer": "string"}},
    {{"question": "string", "answer": "string"}},
    {{"question": "string", "answer": "string"}}
  ]
}}"""

    payload = {
        "model": model,
        "max_tokens": 8192,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]
    }

    for attempt in range(len(providers) + 3):
        resp = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180
        )
        if resp.status_code >= 400:
            next_idx = provider_idx + 1
            if next_idx < len(providers):
                provider_idx = next_idx
                name, api_url, api_key, model = providers[provider_idx]
                print(f"Provider {providers[provider_idx-1][0]} error {resp.status_code} — rotating to {name} [{provider_idx+1}/{len(providers)}]")
                payload["model"] = model
            else:
                print(f"All {len(providers)} providers exhausted — sleeping 30s then restarting rotation")
                time.sleep(30)
                provider_idx = 0
                name, api_url, api_key, model = providers[0]
                payload["model"] = model
            continue
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        content = re.sub(r'^```(?:json)?\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content)
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON parse error (attempt {attempt+1}/5): {e} — retrying LLM call")
            continue
    raise ValueError("Failed after 5 retries")

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
        "author": {
            "@id": AUTHOR_ID,
            "@type": "Person",
            "name": "Luke Anthony",
            "url": "https://howmindswork.org",
            "sameAs": AUTHOR_SAME_AS,
        },
        "publisher": {
            "@type": "Organization",
            "name": "How Minds Work",
            "url": "https://howmindswork.org",
            "logo": {
                "@type": "ImageObject",
                "url": "https://blog.howmindswork.org/assets/og-default.jpg"
            }
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "image": f"{BLOG_URL}/assets/og-default.jpg",
    }

def breadcrumb_schema(url, title):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://howmindswork.org"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": BLOG_URL + "/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": url},
        ]
    }

def render_html(post, kw, date_str, date_iso, post_url):
    takeaways_li = "\n".join(f"<li>{t}</li>" for t in post["key_takeaways"])
    body_content = sections_html(post["sections"], kw)
    faq_content = faq_html(post["faq"])
    a_schema = json.dumps(article_schema(post, kw, post_url, date_iso), indent=2)
    f_schema = json.dumps(faq_schema(post["faq"]), indent=2)
    b_schema = json.dumps(breadcrumb_schema(post_url, post["title"]), indent=2)

    title_escaped = post['title'].replace('"', '&quot;').replace("'", "&#39;")
    meta_escaped = post['meta_description'].replace('"', '&quot;').replace("'", "&#39;")
    og_image_url = f"{BLOG_URL}/assets/posts/{kw['slug']}-og.webp"
    i_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "ImageObject",
        "contentUrl": og_image_url,
        "name": post["title"],
        "description": post["meta_description"][:150],
        "caption": f"{post['title']} — How Minds Work grief healing guide",
        "encodingFormat": "image/webp",
        "width": 1200,
        "height": 630,
        "author": {"@type": "Organization", "name": "How Minds Work", "url": "https://blog.howmindswork.org"},
        "copyrightNotice": "© 2026 How Minds Work"
    }, indent=2)

    html = f"""<!DOCTYPE html>
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
<meta property="og:image" content="{og_image_url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og_image_url}">
<link rel="canonical" href="{post_url}">
<link rel="stylesheet" href="/assets/style.css">
<script type="application/ld+json">
{a_schema}
</script>
<script type="application/ld+json">
{f_schema}
</script>
<script type="application/ld+json">
{b_schema}
</script>
<script type="application/ld+json">
{i_schema}
</script>
</head>
<body>
<nav><div class="container">
  <a href="https://howmindswork.org" class="nav-brand">How Minds Work</a>
  <a href="/" class="nav-link">← All posts</a>
</div></nav>

<header class="post-header"><div class="container">
  <div class="post-meta">
    <span>{date_str}</span>
    <span>·</span>
    <a href="/about/">By Luke</a>
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
  <img src="/assets/luke.png" alt="Luke">
  <div>
    <p class="author-name">Luke</p>
    <p class="author-bio">Creator of The Emotional Completion Ritual. Writes about grief processing, somatic healing, and emotional completion at How Minds Work. <a href="/about/">About Luke →</a></p>
  </div>
</div>

</article>
</div></main>

<footer><div class="container">
  <span>© 2026 How Minds Work</span>
  <span><a href="/">Blog</a> · <a href="https://howmindswork.org">Products</a> · <a href="/about/">About</a></span>
</div></footer>
<script src="/assets/click.js"></script>
</body>
</html>"""
    return inject_pillar_link(html)

def word_overlap(a, b):
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / len(a_words | b_words)

def get_recent_titles(n=10):
    """Return up to n most-recently-modified post titles extracted from index.html <h1>."""
    if not POSTS_DIR.exists():
        return []
    dirs = sorted(
        [d for d in POSTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )[:n]
    titles = []
    for d in dirs:
        html_file = d / "index.html"
        if not html_file.exists():
            continue
        text = html_file.read_text(errors="ignore")
        m = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.IGNORECASE | re.DOTALL)
        if m:
            # Strip any inner tags
            raw = re.sub(r'<[^>]+>', '', m.group(1))
            titles.append(raw.strip())
    return titles

def inject_pillar_link(body_html):
    """Scan body_html for pillar keywords; inject one link block before </article>."""
    if not PILLAR_MAP:
        return body_html
    body_lower = body_html.lower()
    # Multi-word keywords checked before single-word to avoid partial matches
    sorted_keys = sorted(PILLAR_MAP.keys(), key=len, reverse=True)
    for keyword in sorted_keys:
        if keyword in body_lower:
            entry = PILLAR_MAP[keyword]
            link_block = (
                f'\n<p class="pillar-link">Want to go deeper? '
                f'Read the complete guide: '
                f'<a href="{entry["url"]}">{entry["title"]}</a></p>\n'
            )
            return body_html.replace('</article>', link_block + '</article>', 1)
    return body_html

def update_sitemap(data):
    published = [k for k in data["keywords"] if k.get("published")]
    urls = ["""  <url>
    <loc>https://blog.howmindswork.org/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""]
    for kw in published:
        lastmod = kw.get("published_date", datetime.date.today().isoformat())
        img_url = f"{BLOG_URL}/assets/posts/{kw['slug']}-og.webp"
        urls.append(f"""  <url>
    <loc>{BLOG_URL}/posts/{kw['slug']}/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <image:image>
      <image:loc>{img_url}</image:loc>
    </image:image>
  </url>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
  xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
{chr(10).join(urls)}
</urlset>"""
    (ROOT / "blog/sitemap.xml").write_text(xml)
    print(f"Sitemap updated: {len(published)} posts")

def ping_indexnow(url):
    key = os.environ.get("INDEXNOW_KEY", "8a7f3c2b1d9e4f6a")
    try:
        resp = requests.post(
            "https://api.indexnow.org/indexnow",
            json={
                "host": "blog.howmindswork.org",
                "key": key,
                "keyLocation": f"https://blog.howmindswork.org/{key}.txt",
                "urlList": [url],
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print(f"IndexNow ping: {resp.status_code} — {url}")
    except Exception as e:
        print(f"IndexNow ping failed (non-fatal): {e}")

def main():
    data = load_keywords()
    kw = next_keyword(data)
    if not kw:
        print("All keywords published. Add more to keywords.json.")
        return

    print(f"Generating post for: {kw['keyword']}")
    recent_titles = get_recent_titles(10)
    try:
        post = generate_post(kw)
    except Exception as e:
        print(f"All providers failed, skipping this run: {e}")
        return
    # Uniqueness check: max 2 regeneration attempts
    for _attempt in range(2):
        duplicate = next(
            (t for t in recent_titles if word_overlap(post["title"], t) > 0.7),
            None,
        )
        if duplicate is None:
            break
        print(
            f"Title too similar to recent post '{duplicate}' "
            f"(overlap > 0.7) — regenerating (attempt {_attempt + 1}/2)"
        )
        # Patch keyword dict with re-topic instruction for this call only
        kw_patched = dict(kw)
        kw_patched["_regen_hint"] = (
            f"This topic was recently covered. "
            f"Write about a different specific aspect: {kw['keyword']}"
        )
        # Temporarily inject hint into user message via a thin wrapper
        orig_keyword = kw_patched["keyword"]
        kw_patched["keyword"] = (
            f"{orig_keyword} — NOTE: {kw_patched['_regen_hint']}"
        )
        post = generate_post(kw_patched)
    else:
        # After 2 failed attempts, proceed with whatever was generated last
        pass

    if kw.get("planned_date"):
        today = datetime.date.fromisoformat(kw["planned_date"])
    else:
        today = datetime.date.today()
    date_str = today.strftime("%B %d, %Y")
    date_iso = today.isoformat()
    post_url = f"{BLOG_URL}/posts/{kw['slug']}/"

    post_dir = POSTS_DIR / kw["slug"]
    post_dir.mkdir(parents=True, exist_ok=True)
    html = render_html(post, kw, date_str, date_iso, post_url)
    (post_dir / "index.html").write_text(html)
    print(f"Written: blog/posts/{kw['slug']}/index.html")
    make_og(post["title"], kw["slug"])
    subprocess.run(
        ["python3", str(SCRIPTS / "auto_linker.py"), kw["slug"]],
        check=False,
        cwd=str(ROOT),
    )

    for entry in data["keywords"]:
        if entry["slug"] == kw["slug"]:
            entry["published"] = True
            entry["published_date"] = date_iso
            entry["post_title"] = post["title"]
            entry["meta_description"] = post["meta_description"]
    save_keywords(data)

    subprocess.run(["python3", str(SCRIPTS / "render_index.py")], check=True)

    update_sitemap(data)

    ping_indexnow(post_url)

if __name__ == "__main__":
    main()
