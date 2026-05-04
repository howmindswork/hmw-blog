import sys
sys.path.insert(0, '/home/luke/hmw-blog')
from scripts.auto_linker import find_link_opportunities, inject_links

SAMPLE_HTML = """<article class="post-body">
<p><strong>Somatic healing helps process grief through the body.</strong></p>
<h2>What is breathwork for grief?</h2>
<p>Breathwork for grief involves breathing techniques that help release stored emotions.</p>
<p>The nervous system holds grief in specific patterns that somatic exercises can release.</p>
</article>"""

PUBLISHED_POSTS = [
    {"slug": "breathwork-for-grief", "post_title": "Breathwork for Grief", "keyword": "breathwork for grief"},
    {"slug": "somatic-healing-after-loss", "post_title": "Somatic Healing After Loss", "keyword": "somatic healing after loss"},
]

def test_find_link_opportunities():
    opportunities = find_link_opportunities(SAMPLE_HTML, PUBLISHED_POSTS, current_slug="new-post")
    slugs = [o["slug"] for o in opportunities]
    assert "breathwork-for-grief" in slugs

def test_inject_links_max_3():
    many_posts = [{"slug": f"post-{i}", "post_title": f"Post {i}", "keyword": f"grief technique {i}"} for i in range(10)]
    html = "<p>" + " ".join(f"grief technique {i}" for i in range(10)) + "</p>"
    result = inject_links(html, many_posts, current_slug="other")
    link_count = result.count('<a href=')
    assert link_count <= 3

def test_inject_links_no_self_link():
    posts = [{"slug": "breathwork-for-grief", "post_title": "Breathwork for Grief", "keyword": "breathwork for grief"}]
    html = "<p>This covers breathwork for grief in detail.</p>"
    result = inject_links(html, posts, current_slug="breathwork-for-grief")
    assert '<a href=' not in result
