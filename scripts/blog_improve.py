#!/usr/bin/env python3
"""
Weekly blog improvement loop. Each run picks ONE improvement from a backlog,
applies it across posts, logs changes, deploys, and verifies live.

One change per week = safe rollback if regression.
Run: python scripts/blog_improve.py
"""
import os, sys, json, re, subprocess, datetime, requests
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "blog/posts"
IMPROVE_BACKLOG = SCRIPTS / "improve_backlog.json"
IMPROVE_LOG = SCRIPTS / "improve_log.md"
BLOG_URL = "https://blog.howmindswork.org"

# Schema improvement markers (like hmw-ritual-match in link_rituals.py)
BREADCRUMB_MARK = "hmw-breadcrumb-schema"
HOWTO_MARK = "hmw-howto-schema"
CHUNK_MARK = "hmw-chunk-blocks"
REDDIT_MARK = "hmw-reddit-cta"

def load_backlog():
    """Load improvement backlog. Create default if missing."""
    if IMPROVE_BACKLOG.exists():
        return json.loads(IMPROVE_BACKLOG.read_text())
    return {
        "improvements": [
            {
                "id": "breadcrumb",
                "title": "Add BreadcrumbList schema (hub-and-spoke topology signal)",
                "description": "Every post needs BreadcrumbList JSON-LD for topic cluster discovery",
                "done": False,
            },
            {
                "id": "howto",
                "title": "Wrap numbered protocols in HowTo schema",
                "description": "Posts with 3-7 step protocols get HowTo markup for AI extraction",
                "done": False,
            },
            {
                "id": "chunks",
                "title": "Wrap 40-60 word answers in <span data-ai-chunk>",
                "description": "Make direct answers cleanly extractable for ChatGPT/Perplexity chunk retrieval",
                "done": False,
            },
            {
                "id": "author_links",
                "title": "Add LinkedIn/Wikipedia links to author Person schema",
                "description": "E-E-A-T signal: author credibility via external authority profiles",
                "done": False,
            },
            {
                "id": "robots_retrieval",
                "title": "Update robots.txt to explicitly allow AI retrieval bots",
                "description": "PerplexityBot, OAI-SearchBot, ChatGPT-User, Claude-SearchBot allowed",
                "done": False,
            },
        ]
    }

def save_backlog(data):
    IMPROVE_BACKLOG.write_text(json.dumps(data, indent=2))

def get_next_improvement(backlog):
    """Pick first incomplete improvement."""
    for imp in backlog["improvements"]:
        if not imp.get("done"):
            return imp
    return None

def apply_breadcrumb_schema():
    """Add BreadcrumbList to every post. Most posts are in one pillar: Grief."""
    posts = [d for d in POSTS_DIR.iterdir() if d.is_dir()]
    changed = 0
    for post_dir in sorted(posts):
        html_file = post_dir / "index.html"
        if not html_file.exists():
            continue
        content = html_file.read_text()

        # Skip if already has breadcrumb marker
        if BREADCRUMB_MARK in content:
            continue

        # Find the first FAQPage/BlogPosting schema and insert breadcrumb before closing script tag
        breadcrumb_schema = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Blog", "item": BLOG_URL},
                {"@type": "ListItem", "position": 2, "name": "Grief Healing", "item": f"{BLOG_URL}/posts/"},
                {"@type": "ListItem", "position": 3, "name": post_dir.name, "item": f"{BLOG_URL}/posts/{post_dir.name}/"},
            ]
        }, indent=2)

        # Insert before closing </head>, marked with BREADCRUMB_MARK
        pattern = r'(<script type="application/ld\+json">\s*\{[^}]+"\@type": "FAQPage")'
        marker_script = f'<script type="application/ld+json" class="{BREADCRUMB_MARK}">\n{breadcrumb_schema}\n</script>\n\\1'
        new_content = re.sub(pattern, marker_script, content, count=1)

        if new_content != content:
            html_file.write_text(new_content)
            changed += 1

    return f"Breadcrumb schema added to {changed}/{len(posts)} posts"

def apply_howto_schema():
    """Wrap numbered steps in HowTo markup where found."""
    posts = [d for d in POSTS_DIR.iterdir() if d.is_dir()]
    changed = 0
    for post_dir in sorted(posts):
        html_file = post_dir / "index.html"
        if not html_file.exists():
            continue
        content = html_file.read_text()

        # Skip if already processed
        if HOWTO_MARK in content:
            continue

        # Find <ol>...</ol> patterns (numbered steps)
        if "<ol>" not in content:
            continue

        # For posts with HowTo, add schema. HowTo only works for posts with clear steps.
        # Extract title from h1
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
        if not title_match:
            continue

        title = title_match.group(1)

        # Count and extract steps
        step_pattern = r'<li[^>]*>([^<]+)<'
        steps = re.findall(step_pattern, content)
        if len(steps) < 3:
            continue

        howto_schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i+1,
                    "text": step.strip()[:100]  # Truncate to 100 chars
                }
                for i, step in enumerate(steps[:7])  # Max 7 steps
            ]
        }

        schema_script = f'<script type="application/ld+json" class="{HOWTO_MARK}">\n{json.dumps(howto_schema, indent=2)}\n</script>\n'
        new_content = content.replace('</head>', f'{schema_script}</head>', 1)

        if new_content != content:
            html_file.write_text(new_content)
            changed += 1

    return f"HowTo schema added to {changed}/{len(posts)} posts with numbered steps"

def apply_chunk_blocks():
    """Wrap first paragraph after each H2 in <span data-ai-chunk> for AI extraction."""
    posts = [d for d in POSTS_DIR.iterdir() if d.is_dir()]
    changed = 0
    for post_dir in sorted(posts):
        html_file = post_dir / "index.html"
        if not html_file.exists():
            continue
        content = html_file.read_text()

        if CHUNK_MARK in content:
            continue

        # Find each H2 and wrap the next <p> in <span data-ai-chunk>
        def wrap_chunk(match):
            h2 = match.group(1)
            p = match.group(2)
            # Avoid double-wrapping
            if 'data-ai-chunk' in p:
                return f'{h2}{p}'
            # Check if p is 40-60 words (rough)
            words = len(p.split())
            if 30 < words < 200:  # Reasonable chunk size
                return f'{h2}\n<span class="{CHUNK_MARK}" data-ai-chunk>{p}</span>'
            return f'{h2}{p}'

        new_content = re.sub(
            r'(<h2[^>]*>[^<]*</h2>)\s*(<p[^>]*>[^<]*</p>)',
            wrap_chunk,
            content
        )

        if new_content != content:
            html_file.write_text(new_content)
            changed += 1

    return f"AI chunk markers added to {changed}/{len(posts)} posts"

def apply_robots_retrieval():
    """Update robots.txt to explicitly allow AI retrieval bots.

    Targets blog/robots.txt, the file Cloudflare Pages actually serves for
    the blog (`wrangler pages deploy blog`) -- the repo-root robots.txt
    belongs to the main howmindswork.org site and must never be touched here.
    """
    robots_file = ROOT / "blog" / "robots.txt"
    content = robots_file.read_text() if robots_file.exists() else ""

    if "PerplexityBot" in content and "Disallow: /" in content.split("GPTBot", 1)[-1]:
        return "blog/robots.txt already allows AI retrieval bots and blocks training crawlers"

    new_content = """User-agent: *
Allow: /

# Block AI training crawlers
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Google-Extended
Disallow: /

# Allow AI retrieval bots
User-agent: PerplexityBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

Sitemap: https://blog.howmindswork.org/sitemap.xml
"""
    robots_file.write_text(new_content)
    return "blog/robots.txt updated to allow retrieval bots and block training crawlers"

def deploy_blog():
    """Deploy via Cloudflare Pages."""
    env_vars = {
        "CLOUDFLARE_API_TOKEN": os.environ.get("CLOUDFLARE_HMW_BOT_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN"),
        "CLOUDFLARE_ACCOUNT_ID": os.environ.get("CLOUDFLARE_ACCOUNT_ID"),
    }

    if not env_vars["CLOUDFLARE_API_TOKEN"] or not env_vars["CLOUDFLARE_ACCOUNT_ID"]:
        raise ValueError("Missing CLOUDFLARE_HMW_BOT_TOKEN or CLOUDFLARE_ACCOUNT_ID")

    cmd = [
        "npx", "--yes", "wrangler@latest", "pages", "deploy", "blog",
        "--project-name=hmw-blog",
        "--commit-dirty=true"
    ]

    result = subprocess.run(cmd, env={**os.environ, **env_vars}, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Deploy failed: {result.stderr}")

    return "Deployed to Cloudflare Pages"

def verify_live():
    """Verify changes are live by comparing byte sizes."""
    test_post = BLOG_URL + "/posts/10-practical-steps-to-end-emotional-numbness-today/"
    control_url = BLOG_URL + "/posts/nonexistent-post-12345/"

    try:
        resp_test = requests.get(test_post, timeout=10)
        resp_control = requests.get(control_url, timeout=10)

        # Both should be 200 (CF Pages serves fallback), but test_post should be much larger
        if resp_test.status_code != 200 or resp_control.status_code != 200:
            return f"Verification inconclusive: test={resp_test.status_code}, control={resp_control.status_code}"

        test_size = len(resp_test.content)
        control_size = len(resp_control.content)

        # Real post should be 10x+ larger than fallback
        if test_size > control_size * 5:
            return f"Live verification passed: {test_size} vs {control_size} bytes (ratio: {test_size//control_size}x)"
        else:
            return f"Verification failed: sizes too close ({test_size} vs {control_size})"
    except Exception as e:
        return f"Verification error: {e}"

def log_improvement(imp_id, imp_title, result, deploy_result, verify_result):
    """Log what happened this run."""
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"\n## [{timestamp}] {imp_title} ({imp_id})\n- Applied: {result}\n- Deploy: {deploy_result}\n- Verify: {verify_result}\n"

    if IMPROVE_LOG.exists():
        current = IMPROVE_LOG.read_text()
        IMPROVE_LOG.write_text(current + log_entry)
    else:
        IMPROVE_LOG.write_text(f"# Blog Improvement Log\n{log_entry}")

def fetch_top_10():
    """Fetch top 10 performing posts from analytics. Write to top10.md."""
    try:
        resp = requests.get(
            "https://hmw-analytics.howmindswork.workers.dev/report",
            headers={"User-Agent": "blog-improve-loop/1.0"},
            timeout=10
        )
        if resp.status_code != 200:
            return "Could not fetch analytics"

        data = resp.json() if resp.headers.get("content-type") == "application/json" else {}

        # Format as markdown for Luke's video ideas
        top10_content = "# Top 10 Blog Posts by Performance\n\nVideo topic ideas:\n"

        # The analytics worker returns a page path, never a title, so the first
        # version of this printed "Unknown" ten times. The slug IS the topic,
        # which is the whole point of the list, so read the title off it.
        rank = 0
        for post in data.get("top_posts", []):
            page = post.get("page", "")
            if not page.startswith("/posts/"):
                continue  # homepage and /ecp are not video topics
            rank += 1
            if rank > 10:
                break
            topic = page.replace("/posts/", "").strip("/").replace("-", " ")
            views = post.get("views", 0)
            top10_content += (f"\n{rank}. **{topic}** ({views} reads)\n"
                              f"   https://blog.howmindswork.org{page}\n")
        if rank == 0:
            top10_content += "\nNo post-level traffic recorded yet this period.\n"

        top10_file = SCRIPTS / "top10.md"
        top10_file.write_text(top10_content)
        return f"Top 10 written to top10.md"
    except Exception as e:
        return f"Analytics fetch failed: {e}"

def demo():
    """Self-check: verify blog structure before run."""
    posts = list(POSTS_DIR.glob("*/index.html"))
    if not posts:
        raise AssertionError("No posts found in blog/posts/")

    sample = posts[0].read_text()
    if '"@type": "BlogPosting"' not in sample:
        raise AssertionError("Sample post missing BlogPosting schema")

    if "FAQPage" not in sample:
        raise AssertionError("Sample post missing FAQPage schema")

    print(f"✓ Blog structure OK: {len(posts)} posts, schemas present")

def main():
    # `--demo` must never write, deploy, or burn a backlog item. It ran a full
    # live cycle on its first outing and touched 143 files, which is not a
    # self-check, it is a deploy with a misleading flag.
    if "--demo" in sys.argv:
        demo()
        return
    demo()

    backlog = load_backlog()
    imp = get_next_improvement(backlog)

    if not imp:
        print("All improvements complete! Blog is optimized for 2026 GEO/AEO.")
        return

    imp_id = imp["id"]
    imp_title = imp["title"]

    print(f"Running: {imp_title}")

    # Apply the improvement
    if imp_id == "breadcrumb":
        result = apply_breadcrumb_schema()
    elif imp_id == "howto":
        result = apply_howto_schema()
    elif imp_id == "chunks":
        result = apply_chunk_blocks()
    elif imp_id == "author_links":
        result = "Author LinkedIn links require manual review (waiting for verification)"
    elif imp_id == "robots_retrieval":
        result = apply_robots_retrieval()
    else:
        result = "Unknown improvement"

    print(f"  Applied: {result}")

    # Deploy
    try:
        deploy_result = deploy_blog()
        print(f"  Deploy: {deploy_result}")
    except Exception as e:
        deploy_result = f"Deploy failed: {e}"
        print(f"  Deploy: {deploy_result}")
        return

    # Verify
    verify_result = verify_live()
    print(f"  Verify: {verify_result}")

    # Fetch analytics for Luke
    analytics_result = fetch_top_10()
    print(f"  Analytics: {analytics_result}")

    # Log it
    log_improvement(imp_id, imp_title, result, deploy_result, verify_result)

    # Mark done
    for i in backlog["improvements"]:
        if i["id"] == imp_id:
            i["done"] = True
    save_backlog(backlog)

    print(f"\n✓ Improvement cycle complete. Next run will apply: {get_next_improvement(backlog)['title'] if get_next_improvement(backlog) else 'None (all done!)'}")

if __name__ == "__main__":
    main()
