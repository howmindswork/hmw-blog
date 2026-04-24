#!/usr/bin/env python3
import json
import re
from pathlib import Path
from datetime import datetime

def load_published():
    """Load and filter published posts from keywords.json"""
    with open('scripts/keywords.json', 'r') as f:
        keywords = json.load(f)
    
    published = [
        post for post in keywords
        if post.get('published') and post.get('post_title')
    ]
    return published

def post_card_html(post):
    """Generate HTML card for a single post"""
    date_str = post.get('published_date', 'Unknown')
    title = post.get('post_title', 'Untitled')
    slug = post.get('slug', '')
    excerpt = post.get('post_excerpt', '')
    
    return f'''<article class="post-card">
        <time class="post-date">{date_str}</time>
        <h2><a href="/blog/{slug}">{title}</a></h2>
        <p class="post-excerpt">{excerpt}</p>
    </article>'''

def render():
    """Render blog index with all published posts"""
    posts = load_published()
    posts.sort(key=lambda p: p.get('published_date', ''), reverse=True)
    
    cards_html = '\n            '.join(post_card_html(p) for p in posts)
    
    with open('blog/index.html', 'r') as f:
        html = f.read()
    
    pattern = r'(<div class="posts-grid" id="posts">)\s*(.*?)\s*(</div>)'
    replacement = f'\\1\n            {cards_html}\n        \\3'
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    with open('blog/index.html', 'w') as f:
        f.write(html)
    
    print(f"Rendered blog index with {len(posts)} posts")

if __name__ == '__main__':
    render()
