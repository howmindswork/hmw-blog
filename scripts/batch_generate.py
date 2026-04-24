#!/usr/bin/env python3
"""
Batch post generator — generates all unpublished keywords with pre-assigned dates.
Run locally: python scripts/batch_generate.py
"""
import json, datetime, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
KEYWORDS_FILE = SCRIPTS / "keywords.json"

# Pre-assigned dates for unpublished posts — spread across past weeks
PLANNED_DATES = [
    "2026-04-01",
    "2026-04-03",
    "2026-04-05",
    "2026-04-07",
    "2026-04-09",
    "2026-04-11",
    "2026-04-13",
    "2026-04-15",
    "2026-04-17",
    "2026-04-18",
    "2026-04-20",
    "2026-04-21",
    "2026-04-22",
    "2026-04-23",
    "2026-04-24",
]

def main():
    data = json.loads(KEYWORDS_FILE.read_text())
    unpublished = [k for k in data["keywords"] if not k.get("published")]

    print(f"Found {len(unpublished)} unpublished posts to generate")

    for i, kw in enumerate(unpublished):
        planned_date = PLANNED_DATES[i] if i < len(PLANNED_DATES) else datetime.date.today().isoformat()
        print(f"\n[{i+1}/{len(unpublished)}] Generating: {kw['keyword']} → {planned_date}")

        # Inject planned_date into the keyword entry temporarily
        data_copy = json.loads(KEYWORDS_FILE.read_text())
        for entry in data_copy["keywords"]:
            if entry["slug"] == kw["slug"]:
                entry["planned_date"] = planned_date
        KEYWORDS_FILE.write_text(json.dumps(data_copy, indent=2))

        result = subprocess.run(
            ["python3", str(SCRIPTS / "generate_post.py")],
            capture_output=False,
            cwd=str(ROOT)
        )

        if result.returncode != 0:
            print(f"ERROR generating {kw['slug']} — stopping")
            sys.exit(1)

        # Small wait between posts (Groq is fast, just being polite)
        if i < len(unpublished) - 1:
            print("Waiting 5s before next post...")
            time.sleep(5)

    print(f"\nDone. Generated {len(unpublished)} posts.")

if __name__ == "__main__":
    main()
