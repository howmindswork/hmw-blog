import sys
sys.path.insert(0, '/home/luke/hmw-blog')
from scripts.generate_post import article_schema, breadcrumb_schema

def test_article_schema_has_sameAs():
    kw = {"slug": "test-slug"}
    result = article_schema({"title": "T", "meta_description": "D"}, kw, "https://blog.howmindswork.org/posts/test-slug/", "2026-05-04")
    author = result["author"]
    assert "@id" in author
    assert "sameAs" in author
    assert any("instagram" in s for s in author["sameAs"])

def test_article_schema_publisher_is_org():
    kw = {"slug": "test-slug"}
    result = article_schema({"title": "T", "meta_description": "D"}, kw, "https://blog.howmindswork.org/posts/test-slug/", "2026-05-04")
    assert result["publisher"]["@type"] == "Organization"
    assert "logo" in result["publisher"]

def test_breadcrumb_schema():
    result = breadcrumb_schema("https://blog.howmindswork.org/posts/somatic-healing-after-loss/", "Somatic Healing After Loss")
    assert result["@type"] == "BreadcrumbList"
    assert len(result["itemListElement"]) == 3
