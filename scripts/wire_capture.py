#!/usr/bin/env python3
"""Wire the star-audio email popup + analytics into every page that's missing them.

Idempotent: safe to re-run. Skips sales pages, where an opt-in popup for a free
audio competes with the paid purchase decision instead of capturing a lost visitor.

    python3 scripts/wire_capture.py --dry-run
    python3 scripts/wire_capture.py
"""
import argparse
import re
import sys
from pathlib import Path

BLOG = Path(__file__).resolve().parent.parent / "blog"

POPUP = '<script defer src="/assets/popup-star-audio.js"></script>'
TRACK = '<script defer src="/assets/hmw-track.js"></script>'

# Pages whose whole job is closing a sale. A free-audio popup here trades a
# $97 decision for an email address — a bad trade on the only pages with intent.
NO_POPUP = {
    "emotional-completion-ritual-guide",
    "emotional-completion-system",
    "neuro-flip-protocol",
}

# 16 pages promise a free audio and link to the $97 guide. Point them at the
# actual free audio product so the click lands on what the copy promised.
BAD_CTA = re.compile(
    r'(<a[^>]*href=")https://lukeisthere\.gumroad\.com/l/EmotionalCompletionGuide'
    r'([^"]*"[^>]*>Get the free audio</a>)'
)
GOOD_CTA = r"\1https://lukeisthere.gumroad.com/l/StoneReleaseRitualAudio\2"


def wants_popup(path):
    return not any(part in NO_POPUP for part in path.parts)


def process(path, dry_run):
    html = path.read_text(encoding="utf-8", errors="replace")
    original = html
    added = []

    if "popup-star-audio" not in html and wants_popup(path):
        added.append("popup")
    if "hmw-track" not in html:
        added.append("analytics")

    if added:
        tags = ""
        if "popup" in added:
            tags += POPUP + "\n"
        if "analytics" in added:
            tags += TRACK + "\n"
        # Inject before the final </body>; fall back to </html>, then append.
        if "</body>" in html:
            head, sep, tail = html.rpartition("</body>")
            html = head + tags + sep + tail
        elif "</html>" in html:
            head, sep, tail = html.rpartition("</html>")
            html = head + tags + sep + tail
        else:
            html = html + "\n" + tags

    html, n_cta = BAD_CTA.subn(GOOD_CTA, html)
    if n_cta:
        added.append(f"cta x{n_cta}")

    if html != original and not dry_run:
        path.write_text(html, encoding="utf-8")
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pages = sorted(BLOG.rglob("index.html"))
    if not pages:
        print(f"No pages found under {BLOG}", file=sys.stderr)
        return 1

    tally = {"popup": 0, "analytics": 0, "cta": 0}
    for p in pages:
        for change in process(p, args.dry_run):
            if change.startswith("cta"):
                tally["cta"] += int(change.split("x")[1])
            else:
                tally[change] += 1

    verb = "would add" if args.dry_run else "added"
    print(f"{len(pages)} pages scanned")
    print(f"  {verb} popup:     {tally['popup']}")
    print(f"  {verb} analytics: {tally['analytics']}")
    print(f"  {verb} CTA fixes: {tally['cta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
