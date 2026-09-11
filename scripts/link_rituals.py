#!/usr/bin/env python3
"""Put the matching ritual on every blog post.

The blog gets ~95 reads a week across 59 posts and earns nothing, because a
post about a Celtic grief ritual offers the reader two old Gumroad files and no
ritual. Every offer page at howmindswork.org/offers/<x>/ is a real Stripe sales
page, so this closes that gap: read the post's own words, pick the ritual that
actually matches, and drop one block in above the existing CTA.

    python3 scripts/link_rituals.py --dry-run   # show what each post would get
    python3 scripts/link_rituals.py             # write it into the post files
"""
import re, sys
from collections import Counter
from pathlib import Path

POSTS = Path(__file__).parent.parent / "blog" / "posts"
BASE = "https://howmindswork.org/offers"
MARK = "hmw-ritual-match"  # so a re-run replaces its own block, never stacks

# Each ritual, and the words in a post that mean the reader needs THAT one.
# Ordered most specific first: a post naming "keening" wants Keening, not the
# generic grief pick.
RITUALS = [
    ("keening",        "Keening",       "grief",
     ["keening", "wailing", "lament", "mourning cry", "irish", "celtic"]),
    ("hotoke-okuri",   "Hotoke Okuri",  "heartbreak",
     ["heartbreak", "breakup", "divorce", "left me", "ex-partner", "japanese"]),
    ("fury-song",      "Fury Song",     "anger",
     ["anger", "angry", "rage", "fury", "resentment", "furious"]),
    ("sky-offering",   "Sky Offering",  "abandonment",
     ["abandonment", "abandoned", "estranged", "no contact", "rejected", "left behind"]),
    ("burying-shame",  "Burying Shame", "shame",
     ["shame", "ashamed", "guilt", "guilty", "self-blame", "worthless"]),
    ("memory-rewrite", "Memory Rewrite", "painful memories",
     ["memory", "memories", "flashback", "intrusive thought", "remembering"]),
    ("yoga-nidra",     "Yoga Nidra",    "exhaustion",
     ["yoga nidra", "nidra", "exhaustion", "burnout", "can't sleep", "insomnia", "sleep"]),
    ("breathwork",     "Nadi Shodhana", "anxiety",
     ["breathwork", "breathing", "breath", "holotropic", "nadi", "4-7-8", "somatic breath"]),
    ("neuro-flip",     "Neuro-Flip",    "anxiety",
     ["anxiety", "anxious", "panic", "nervous system", "fight or flight", "dysregulat"]),
    ("receiving-care", "Receiving Care", "self-worth",
     ["self-worth", "asking for help", "receiving", "let people in", "lonely", "alone"]),
    ("star-feeding",   "Star Feeding",  "grief",
     ["grief", "grieving", "loss", "died", "death", "funeral", "bereave", "numb"]),
]


# Every post on this blog says "grief" and "loss" somewhere, so raw word counts
# sent 90 of 137 posts to the same ritual on the first run. A word only earns a
# ritual the click if it is rare across the blog, so the broad-feeling rituals
# score at face value and the specific ones get weighted up.
BROAD = {"star-feeding", "neuro-flip", "breathwork", "receiving-care"}
SPECIFIC_WEIGHT = 4


def pick(text):
    """Score every ritual against the post body, strongest wins."""
    low = text.lower()
    best, best_score = None, 0
    for slug, name, feeling, words in RITUALS:
        weight = 1 if slug in BROAD else SPECIFIC_WEIGHT
        score = weight * sum(low.count(w) for w in words)
        if score > best_score:
            best, best_score = (slug, name, feeling), score
    return best


def block(slug, name, feeling, post_slug):
    utm = f"?utm_source=blog&utm_medium=ritual_match&utm_campaign={post_slug}"
    return (
        f'\n<aside class="{MARK}" style="margin:2.5rem 0;padding:1.5rem;'
        f'border:1px solid rgba(255,255,255,.18);border-radius:10px">\n'
        f'  <p style="margin:0 0 .5rem;opacity:.75;font-size:.9rem">'
        f'The ritual for this</p>\n'
        f'  <p style="margin:0 0 1rem"><strong>{name}</strong> is the guided '
        f'{feeling} ritual. About 20 minutes, done once, on your own.</p>\n'
        f'  <a href="{BASE}/{slug}/{utm}" '
        f'style="font-weight:600">Listen to {name}</a>\n'
        f'</aside>\n'
    )


def main():
    dry = "--dry-run" in sys.argv
    posts = sorted(POSTS.glob("*/index.html"))
    counts, changed = Counter(), 0

    for path in posts:
        html = path.read_text(encoding="utf-8")
        # Strip any block a previous run left, so this is safe to re-run.
        html = re.sub(rf'\n<aside class="{MARK}".*?</aside>\n', "\n", html,
                      flags=re.DOTALL)
        body = re.sub(r"<[^>]+>", " ", html)
        hit = pick(body)
        if not hit:
            print(f"  no match: {path.parent.name}")
            continue
        slug, name, feeling = hit
        counts[name] += 1
        new = block(slug, name, feeling, path.parent.name)

        # Above the existing CTA if there is one, else at the end of the article.
        for anchor in ('<div class="cta', "<footer", "</article>"):
            if anchor in html:
                html = html.replace(anchor, new + anchor, 1)
                break
        else:
            html += new
        if not dry:
            path.write_text(html, encoding="utf-8")
        changed += 1

    print(f"\n{'would link' if dry else 'linked'} {changed} of {len(posts)} posts")
    for name, c in counts.most_common():
        print(f"  {c:>4}  {name}")


def demo():
    """Self-check: the picker must route obvious posts to the obvious ritual."""
    cases = [
        ("She could not stop crying at the funeral, the grief was constant", "Star Feeding"),
        ("holotropic breathwork classes near me, breathing exercises", "Nadi Shodhana"),
        ("yoga nidra for sleep and exhaustion, nidra practice", "Yoga Nidra"),
        ("the anger and rage after betrayal, furious every day", "Fury Song"),
        ("keening is the old irish lament for the dead", "Keening"),
    ]
    for text, want in cases:
        got = pick(text)
        assert got and got[1] == want, f"{text[:35]!r} -> {got and got[1]} want {want}"
    print("picker self-check passed")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
