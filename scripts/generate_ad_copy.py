#!/usr/bin/env python3
"""Daily ad copy GENERATOR for the $97 grief ritual offer.

Replaces the fixed 10-variation bank (content/ad-copy/grief-ritual/bank.md,
still kept as a style exemplar / do-not-edit reference — parsed by the older
scripts/daily_ad_copy.py) with LLM-generated copy drawn from a pool of real,
citable research anchors (content/ad-copy/grief-ritual/anchors.json).

Reuses the provider-fallback rotation from scripts/generate_post.py
(_build_providers: Gemini -> Cerebras -> Groq -> OpenRouter) instead of
duplicating it.

Selection: picks one (anchor, angle) pair that has not been used in the last
7 days, tracked in content/ad-copy/grief-ritual/usage_ledger.json. Every
generated post is also logged to
content/ad-copy/grief-ritual/performance_ledger.json for later
winner/loser/retest classification once real metrics come in.

Hard constraint (baked into the system prompt, not just this docstring):
no invented studies, no invented statistics, no sacred practice attributed
to a named living tribe. Every claim must trace to the single anchor given.
This is a paid, health-adjacent product — a fabricated claim is FTC /
platform health-misinformation exposure, and the account is the business's
core asset.

Usage:
    python3 scripts/generate_ad_copy.py                # generate today's post
    python3 scripts/generate_ad_copy.py --dry-run       # skip the LLM call, use a stub
    python3 scripts/generate_ad_copy.py --anchor norton_gino_2014 --angle belief_independence
    python3 scripts/generate_ad_copy.py --list-anchors
"""

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import random
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_post import _build_providers  # noqa: E402  (reuse, do not duplicate)

ROOT = Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "content" / "ad-copy" / "grief-ritual"
ANCHORS_FILE = BANK_DIR / "anchors.json"
USAGE_LEDGER = BANK_DIR / "usage_ledger.json"
PERF_LEDGER = BANK_DIR / "performance_ledger.json"
OUT_DIR = ROOT / "out" / "ad-copy"

USAGE_WINDOW_DAYS = 7

PRODUCT_NAME = "the $97 grief ritual (Stone Release / Emotional Completion Guide)"

SYSTEM_PROMPT = f"""You write direct-response social ad copy (on-screen text + caption) \
for {PRODUCT_NAME}. You are given ONE research anchor and ONE angle on that anchor. \
Write in the voice of the existing bank of ads: a forbidden/suppressed-knowledge \
frame, credibility built ONLY from the exact names/dates/journal given to you below \
(never invent your own to sound more specific), a named enemy whose incentives \
explain why this isn't common advice, a tangible low-effort protocol, and an \
identity-indictment close, ending with an open loop to the bio/DM.

HARD CONSTRAINTS (non-negotiable, violate none of them):
1. Do not invent studies, researchers, journals, institutions, or statistics of any \
kind. Use ONLY the citation and core_fact given to you below — do not add numbers, \
percentages, sample sizes, or dates that are not present in that material.
2. Do not attribute any sacred, spiritual, or ceremonial practice to a specific named \
living tribe, indigenous group, or named cultural/ethnic community.
3. Every factual or research claim in your output must trace directly back to the \
single anchor citation provided in this prompt. Do not introduce any other citation, \
study, or data point.
4. Every variation you write must promote the SAME single offer: {PRODUCT_NAME}. \
Never introduce a different product, unrelated topic, or unrelated ritual — only vary \
the angle of approach to this one offer.
5. If you cannot honestly satisfy constraints 1-4 with the material given, write \
copy that is more general/emotional rather than inventing a specific fact to fill \
the gap.
6. Never use an em dash (—) anywhere in the output. Rewrite the sentence instead.

Respond with ONLY a valid JSON object, no markdown fences, matching exactly:
{{
  "title": "short internal title for this variation, e.g. 'The Ritual That Works On Skeptics'",
  "on_screen_text": "the text overlay shown on the video itself, 1-3 short punchy lines",
  "caption": "the full caption body, matching the numbered/emoji style of the existing bank, ending right before the CTA",
  "cta": "one short call to action line, e.g. 'Comment RELEASE and I'll send it to you.'",
  "hashtags": "a single line of 5-8 relevant hashtags"
}}"""


_ID_RE = re.compile(r"^[a-z0-9_]+$")


def load_anchors():
    data = json.loads(ANCHORS_FILE.read_text(encoding="utf-8"))
    pairs = []
    for anchor in data["anchors"]:
        if not _ID_RE.match(anchor["id"]):
            raise ValueError(f"Invalid anchor id {anchor['id']!r} (must match {_ID_RE.pattern})")
        for angle in anchor["angles"]:
            if not _ID_RE.match(angle["id"]):
                raise ValueError(f"Invalid angle id {angle['id']!r} (must match {_ID_RE.pattern})")
            pairs.append((anchor, angle))
    if not pairs:
        raise ValueError(f"No anchor/angle pairs found in {ANCHORS_FILE}")
    return pairs


@contextlib.contextmanager
def _locked(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _atomic_write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def _load_json(path: Path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def pick_anchor_angle(pairs, on_date: dt.date, rng: random.Random):
    """Pick a (anchor, angle) not used in the last USAGE_WINDOW_DAYS days.

    Does NOT record the pick — call record_usage() only after the copy has
    actually been generated and validated, so a failed run doesn't burn a
    pair from the week's eligible pool.

    Falls back to the least-recently-used pair if everything eligible has
    somehow already been used this week (pool is ~30, cadence is 5/day,
    so this should only trigger if the pool shrinks a lot).
    """
    with _locked(USAGE_LEDGER.with_suffix(".lock")):
        ledger = _load_json(USAGE_LEDGER, [])
        cutoff = on_date - dt.timedelta(days=USAGE_WINDOW_DAYS)
        recent_keys = set()
        last_used = {}
        for entry in ledger:
            try:
                used_date = dt.date.fromisoformat(entry["date"])
            except (KeyError, ValueError):
                continue
            key = (entry.get("anchor_id"), entry.get("angle_id"))
            if used_date > cutoff:
                recent_keys.add(key)
            if key not in last_used or used_date > last_used[key]:
                last_used[key] = used_date

        eligible = [(a, g) for a, g in pairs if (a["id"], g["id"]) not in recent_keys]

        if eligible:
            chosen = rng.choice(eligible)
        else:
            # Everything used this week — fall back to the stalest pair.
            chosen = min(pairs, key=lambda ag: last_used.get((ag[0]["id"], ag[1]["id"]), dt.date.min))

    return chosen


def record_usage(anchor, angle, on_date: dt.date):
    """Record that (anchor, angle) was actually used on on_date. Call only
    after generation + validation succeeded."""
    with _locked(USAGE_LEDGER.with_suffix(".lock")):
        ledger = _load_json(USAGE_LEDGER, [])
        ledger.append({
            "date": on_date.isoformat(),
            "anchor_id": anchor["id"],
            "angle_id": angle["id"],
        })
        _atomic_write_json(USAGE_LEDGER, ledger)


def build_user_prompt(anchor, angle):
    return f"""ANCHOR CITATION (use verbatim, do not alter names/dates/journal):
{anchor['citation']}

CORE FACT (the only factual material you may draw on):
{anchor['core_fact']}

ANGLE TO WRITE FROM: {angle['label']}
ANGLE NOTES: {angle['note']}

Write today's variation now, following the system prompt's format and hard constraints."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = "".join(ch for ch in text if ch >= " " or ch in "\n\t")
    return text.strip()


def call_llm(system_prompt: str, user_msg: str, dry_run: bool = False):
    if dry_run:
        return {
            "title": "[DRY RUN] stub variation",
            "on_screen_text": "[DRY RUN] on-screen text stub",
            "caption": "[DRY RUN] caption stub referencing the given anchor only.",
            "cta": "[DRY RUN] Comment RELEASE and I'll send it to you.",
            "hashtags": "#griefjourney #healing #ritual #stonerelease #emotionalhealing",
        }

    providers = _build_providers()
    if not providers:
        raise ValueError("No API keys configured — set GEMINI_API_KEY, CEREBRAS_API_KEY, "
                          "GROQ_API_KEY(_N), or OPENROUTER_API_KEY")

    provider_idx = 0
    api_url, api_key, model = providers[0][1], providers[0][2], providers[0][3]
    payload = {
        "model": model,
        "max_tokens": 8192,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    }

    for attempt in range(len(providers) + 3):
        try:
            resp = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            cleaned = _strip_fences(raw)
            return json.loads(cleaned)
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
            print(f"[generate_ad_copy] provider {providers[provider_idx][0]} failed: {exc}",
                  file=sys.stderr)
            provider_idx = (provider_idx + 1) % len(providers)
            api_url, api_key, model = (
                providers[provider_idx][1], providers[provider_idx][2], providers[provider_idx][3]
            )
            payload["model"] = model
            if provider_idx == 0:
                time.sleep(30)

    raise ValueError("Failed after exhausting provider rotation")


_NUMERIC_RE = re.compile(r"\b\d[\d,.]*%?\b")
_TRIBE_TERMS = (
    "lakota", "navajo", "cherokee", "sioux", "apache", "hopi", "maori", "aboriginal",
    "inuit", "cree", "iroquois", "zulu", "shaman", "shamanic",
)


def validate_copy(copy: dict, anchor: dict) -> list:
    """Return a list of fabrication-risk problems found in the generated copy.
    Empty list = passed. This is a backstop for the system prompt's hard
    constraints, not a replacement for them."""
    problems = []
    source_text = f"{anchor.get('citation', '')} {anchor.get('core_fact', '')}".lower()
    source_numbers = set(_NUMERIC_RE.findall(source_text))
    check_text = (
        f"{copy.get('on_screen_text', '')} {copy.get('caption', '')} "
        f"{copy.get('title', '')} {copy.get('cta', '')} {copy.get('hashtags', '')}"
    )

    for match in _NUMERIC_RE.findall(check_text):
        if match.lower() not in source_numbers:
            problems.append(f"number/stat not present in anchor source material: {match!r}")

    lower_check = check_text.lower()
    for term in _TRIBE_TERMS:
        if term in lower_check and term not in source_text:
            problems.append(f"possible named-tribe/ethnic-group reference not in anchor: {term!r}")

    return problems


def render(anchor, angle, copy, on_date: dt.date) -> str:
    return (
        f"# {on_date.isoformat()} — {anchor['id']} / {angle['id']}: {copy['title']}\n\n"
        f"**ANGLE:** {angle['label']} — {angle['note']}\n\n"
        f"**CITATION:** {anchor['citation']}\n\n"
        f"**ON SCREEN TEXT:** {copy['on_screen_text']}\n\n"
        f"**CAPTION:** {copy['caption']}\n\n"
        f"**CTA:** {copy['cta']}\n\n"
        f"**HASHTAGS:** {copy['hashtags']}\n"
    )


def log_performance(anchor, angle, copy, on_date: dt.date):
    entry = {
        "date": on_date.isoformat(),
        "anchor_id": anchor["id"],
        "angle_id": angle["id"],
        "hook": copy.get("on_screen_text", "")[:200],
        "caption_excerpt": copy.get("caption", "")[:200],
        "platform": None,
        "format": None,
        "pain_point": angle.get("label"),
        "visual_style": None,
        "caption_structure": "forbidden-knowledge / named-enemy / protocol / identity-close",
        "cta": copy.get("cta"),
        "views": 0,
        "watch_time": 0,
        "shares": 0,
        "saves": 0,
        "comments": 0,
        "cta_comments": 0,
        "dms": 0,
        "link_clicks": 0,
        "purchases": 0,
        "revenue": 0,
        "classification": "CONTROL",
    }
    with _locked(PERF_LEDGER.with_suffix(".lock")):
        ledger = _load_json(PERF_LEDGER, [])
        ledger.append(entry)
        _atomic_write_json(PERF_LEDGER, ledger)
    return entry


def post_webhook(url, body, entry):
    payload = json.dumps({
        "date": entry["date"],
        "anchor_id": entry["anchor_id"],
        "angle": entry["angle_id"],
        "text": body,
        "content": body[:1900],
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"webhook: {resp.status}", file=sys.stderr)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"webhook failed (non-fatal): {exc}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--anchor", help="pin a specific anchor id (requires --angle)")
    ap.add_argument("--angle", help="pin a specific angle id (requires --anchor)")
    ap.add_argument("--seed", type=int,
                     help="override the random pick's seed (default: deterministic per-date, "
                          "so a retried run on the same day picks the same pair)")
    ap.add_argument("--dry-run", action="store_true", help="skip the LLM call, use a stub response")
    ap.add_argument("--list-anchors", action="store_true", help="list anchor/angle ids and exit")
    args = ap.parse_args()

    if bool(args.anchor) != bool(args.angle):
        ap.error("--anchor and --angle must be given together")

    pairs = load_anchors()

    if args.list_anchors:
        for anchor, angle in pairs:
            print(f"{anchor['id']:28s} {angle['id']:28s} {angle['label']}")
        return 0

    on_date = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    rng = random.Random(args.seed) if args.seed is not None else random.Random(on_date.toordinal())

    if args.anchor and args.angle:
        matches = [(a, g) for a, g in pairs if a["id"] == args.anchor and g["id"] == args.angle]
        if not matches:
            print(f"No anchor/angle pair {args.anchor}/{args.angle}. Try --list-anchors.",
                  file=sys.stderr)
            return 1
        anchor, angle = matches[0]
    else:
        anchor, angle = pick_anchor_angle(pairs, on_date, rng)

    copy = call_llm(SYSTEM_PROMPT, build_user_prompt(anchor, angle), dry_run=args.dry_run)

    for field in ("title", "on_screen_text", "caption", "cta", "hashtags"):
        if not copy.get(field):
            raise ValueError(f"LLM response missing required field: {field}")

    if not args.dry_run:
        problems = validate_copy(copy, anchor)
        if problems:
            for p in problems:
                print(f"[generate_ad_copy] VALIDATION FAILED: {p}", file=sys.stderr)
            raise ValueError("Generated copy failed fabrication-risk validation — "
                              "not recording usage, not writing output.")

    record_usage(anchor, angle, on_date)

    body = render(anchor, angle, copy, on_date)
    print(body)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{on_date.isoformat()}-{anchor['id']}-{angle['id']}.md").write_text(body, encoding="utf-8")
    (OUT_DIR / "today.md").write_text(body, encoding="utf-8")

    entry = log_performance(anchor, angle, copy, on_date)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(body)

    webhook = os.environ.get("AD_COPY_WEBHOOK_URL", "").strip()
    if webhook and not args.dry_run:
        post_webhook(webhook, body, entry)

    return 0


if __name__ == "__main__":
    sys.exit(main())
