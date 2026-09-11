#!/usr/bin/env python3
"""Daily ad copy rotation for the $97 grief ritual offer.

Picks one variation from content/ad-copy/grief-ritual/bank.md per run, cycling
through the whole bank before repeating anything. Prints it, writes it to
out/ad-copy/, appends it to the GitHub Actions job summary, and POSTs it to
AD_COPY_WEBHOOK_URL if that's set (Slack/Discord/Make/Zapier all accept the shape).

Deterministic by date: the same day always yields the same variation, so a retried
or double-triggered workflow run can't burn two variations or post twice.

Usage:
    python3 scripts/daily_ad_copy.py                 # today's copy
    python3 scripts/daily_ad_copy.py --date 2026-09-14
    python3 scripts/daily_ad_copy.py --id V03        # pin a specific one
    python3 scripts/daily_ad_copy.py --all           # dump the whole bank
    python3 scripts/daily_ad_copy.py --list          # ids + titles + angles
"""

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "content" / "ad-copy" / "grief-ritual" / "bank.md"
OUT_DIR = ROOT / "out" / "ad-copy"
EPOCH = dt.date(2026, 1, 1)

FIELDS = ("ANGLE", "CITATION", "ON SCREEN TEXT", "CAPTION", "CTA", "HASHTAGS")


def parse_bank(path=BANK):
    """Split bank.md into variation dicts. Keys on the '## Vxx — Title' headings."""
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r"^## (V\d+)\s+[—-]\s+(.+)$", text, flags=re.MULTILINE)[1:]
    variations = []
    for i in range(0, len(chunks), 3):
        vid, title, body = chunks[i], chunks[i + 1].strip(), chunks[i + 2]
        # Field labels are bolded and on their own line; a field runs until the
        # next label or the '---' separator ending the variation.
        labels = "|".join(re.escape(f) for f in FIELDS)
        pattern = rf"\*\*({labels}):\*\*[ \t]*(.*?)(?=\n\*\*(?:{labels}):\*\*|\n---\s*$|\Z)"
        found = {m.group(1): m.group(2).strip() for m in
                 re.finditer(pattern, body, flags=re.DOTALL | re.MULTILINE)}
        missing = [f for f in FIELDS if f not in found]
        if missing:
            raise ValueError(f"{vid} is missing field(s): {', '.join(missing)}")
        variations.append({
            "id": vid,
            "title": title,
            "angle": found["ANGLE"],
            "citation": found["CITATION"],
            "on_screen_text": found["ON SCREEN TEXT"],
            "caption": found["CAPTION"],
            "cta": found["CTA"],
            "hashtags": found["HASHTAGS"],
        })
    if not variations:
        raise ValueError(f"No variations parsed from {path}")
    return variations


def pick(variations, on_date):
    """Cycle the full bank before repeating; reshuffle the order each cycle."""
    n = len(variations)
    day = (on_date - EPOCH).days
    cycle, slot = divmod(day, n)
    order = list(range(n))
    random.Random(cycle).shuffle(order)
    return variations[order[slot]]


def render(v, on_date):
    return (
        f"# {on_date.isoformat()} — {v['id']}: {v['title']}\n\n"
        f"**Angle:** {v['angle']}\n\n"
        f"**Citation:** {v['citation']}\n\n"
        f"## ON SCREEN TEXT\n\n{v['on_screen_text']}\n\n"
        f"## CAPTION\n\n{v['caption']}\n\n{v['cta']}\n\n{v['hashtags']}\n"
    )


def post_webhook(url, v, on_date, body):
    payload = json.dumps({
        "date": on_date.isoformat(),
        "id": v["id"],
        "title": v["title"],
        "on_screen_text": v["on_screen_text"],
        "caption": f"{v['caption']}\n\n{v['cta']}\n\n{v['hashtags']}",
        # Slack and Discord both render one of these two keys.
        "text": body,
        "content": body[:1900],
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"webhook: {resp.status}", file=sys.stderr)
            return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        # A dead webhook must not fail the run — the copy is still in the summary
        # and in out/, which is where it's actually read from.
        print(f"webhook failed (non-fatal): {exc}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--id", help="pin a specific variation, e.g. V03")
    ap.add_argument("--all", action="store_true", help="dump every variation")
    ap.add_argument("--list", action="store_true", help="list ids, titles, angles")
    args = ap.parse_args()

    variations = parse_bank()

    if args.list:
        for v in variations:
            print(f"{v['id']}  {v['title']}\n      {v['angle'].splitlines()[0]}")
        return 0

    on_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()

    if args.all:
        for v in variations:
            print(render(v, on_date))
            print("\n" + "=" * 72 + "\n")
        return 0

    if args.id:
        matches = [v for v in variations if v["id"].lower() == args.id.lower()]
        if not matches:
            print(f"No variation with id {args.id!r}. Try --list.", file=sys.stderr)
            return 1
        v = matches[0]
    else:
        v = pick(variations, on_date)

    body = render(v, on_date)
    print(body)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{on_date.isoformat()}-{v['id']}.md").write_text(body, encoding="utf-8")
    (OUT_DIR / "today.md").write_text(body, encoding="utf-8")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(body)

    webhook = os.environ.get("AD_COPY_WEBHOOK_URL", "").strip()
    if webhook:
        post_webhook(webhook, v, on_date, body)

    return 0


if __name__ == "__main__":
    sys.exit(main())
