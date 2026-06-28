#!/usr/bin/env bash
# local_fallback.sh - generate + push a blog post if GitHub Actions has gone dark.
# Runs daily via crontab. Idempotent: skips if a post already landed in the last 36h.
# Logs to /home/luke/hmw-blog/logs/fallback.log
# WSL cron is LOCAL CDT (UTC-5/6), so schedule at a CDT time that does not overlap
# the GitHub Actions run (which fires at 10am ET).

set -euo pipefail

REPO="/home/luke/hmw-blog"
LOG="$REPO/logs/fallback.log"
STAMP="$(date '+%Y-%m-%d %H:%M:%S CDT')"

log() { echo "[$STAMP] $1" | tee -a "$LOG"; }

mkdir -p "$REPO/logs"

# Step 1: check if a post was published in the last 36 hours via git log.
# "blog/posts/" covers both new index.html and updated keywords.json.
RECENT=$(git -C "$REPO" log --since="20 hours ago" --oneline -- blog/posts/ scripts/keywords.json 2>/dev/null | wc -l)

if [ "$RECENT" -gt 0 ]; then
  log "Skipping - a post was already published in the last 20h."
  exit 0
fi

log "No recent post found. Running local generation..."

# Step 2: activate venv and load API keys.
source "$REPO/.venv/bin/activate" 2>/dev/null || true

# Source keys without printing them.
set +e
eval "$(grep -E '^export (GEMINI_API_KEY|GEMINI_API_KEY_BLOG|GEMINI_API_KEY_2|CEREBRAS_API_KEY|GROQ_API_KEY|GROQ_API_KEY_[0-9]|GROQ_API_KEY_NEW|OPENROUTER_API_KEY)' /home/luke/.claude_secrets 2>/dev/null)"
set -e

# Step 3: generate post.
cd "$REPO"
if ! python3 scripts/generate_post.py >> "$LOG" 2>&1; then
  log "ERROR: generate_post.py failed. Check the log above."
  exit 1
fi

# Step 4: check if anything changed.
CHANGED=$(git -C "$REPO" diff --name-only HEAD -- blog/posts/ scripts/keywords.json blog/sitemap.xml blog/index.html 2>/dev/null)

if [ -z "$CHANGED" ]; then
  log "WARNING: script ran but produced no changes. All keywords may be published."
  exit 0
fi

log "Post generated. Files changed: $(echo "$CHANGED" | tr '\n' ' ')"

# Step 5: commit and push - GitHub Actions will then deploy to Cloudflare Pages.
git -C "$REPO" config user.name "HMW Local Bot" 2>/dev/null
git -C "$REPO" config user.email "auto@howmindswork.org" 2>/dev/null
git -C "$REPO" add blog/posts/ scripts/keywords.json blog/sitemap.xml blog/index.html blog/assets/posts/
git -C "$REPO" commit -m "feat(blog): local fallback post $(date +%Y-%m-%d)"
git -C "$REPO" push origin main

log "Done. Post committed and pushed - GitHub will deploy to Cloudflare Pages."
