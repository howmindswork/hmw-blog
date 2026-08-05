#!/usr/bin/env bash
# local_fallback.sh - keep the blog publishing even when GitHub Actions is broken.
# Runs daily via crontab. Two jobs, in order:
#   1. If no post landed in the last 20h, generate one locally.
#   2. Whatever happened above, make sure the LIVE SITE matches the repo.
#      (The GitHub "Blog Publisher" deploy step died on an expired Cloudflare
#      token on 2026-06 and nobody noticed for ~6 weeks: posts kept being
#      written and committed, but 77 of them never reached the live site.
#      That is why this script now deploys itself instead of trusting GitHub.)
# Logs to /home/luke/hmw-blog/logs/fallback.log
# WSL cron is LOCAL CDT (UTC-5/6), so schedule at a CDT time that does not overlap
# the GitHub Actions run (which fires at 10am ET).

set -euo pipefail

REPO="/home/luke/hmw-blog"
LOG="$REPO/logs/fallback.log"
SITE="https://blog.howmindswork.org"
STAMP="$(date '+%Y-%m-%d %H:%M:%S CDT')"

log() { echo "[$STAMP] $1"; }

mkdir -p "$REPO/logs"
cd "$REPO"

# Source keys without printing them. Needed for generation AND for the deploy.
set +e
eval "$(grep -E '^export (GEMINI_API_KEY|GEMINI_API_KEY_BLOG|GEMINI_API_KEY_2|CEREBRAS_API_KEY|GROQ_API_KEY|GROQ_API_KEY_[0-9]|GROQ_API_KEY_NEW|OPENROUTER_API_KEY|CLOUDFLARE_HMW_BOT_TOKEN|CLOUDFLARE_ACCOUNT_ID)' /home/luke/.claude_secrets 2>/dev/null)"
set -e

# Always sync with the remote first. GitHub Actions writes to this same repo, so
# pushing without pulling is what left 28 local commits stranded.
git fetch origin main --quiet
git pull --rebase --quiet origin main || {
  log "ERROR: pull --rebase hit a conflict. Repo left untouched, fix by hand."
  exit 1
}

# ---------- job 1: generate a post if nothing landed recently ----------
RECENT=$(git log --since="20 hours ago" --oneline -- blog/posts/ scripts/keywords.json 2>/dev/null | wc -l)

if [ "$RECENT" -gt 0 ]; then
  log "A post already landed in the last 20h - skipping generation."
else
  log "No recent post found. Running local generation..."
  source "$REPO/.venv/bin/activate" 2>/dev/null || true
  if ! python3 scripts/generate_post.py >> "$LOG" 2>&1; then
    log "ERROR: generate_post.py failed. Check the log above."
  else
    CHANGED=$(git diff --name-only HEAD -- blog/posts/ scripts/keywords.json blog/sitemap.xml blog/index.html 2>/dev/null)
    if [ -z "$CHANGED" ]; then
      log "WARNING: script ran but produced no changes. All keywords may be published."
    else
      log "Post generated: $(echo "$CHANGED" | tr '\n' ' ')"
      git config user.name "HMW Local Bot"
      git config user.email "auto@howmindswork.org"
      git add blog/posts/ scripts/keywords.json blog/sitemap.xml blog/index.html blog/assets/posts/
      git commit -q -m "feat(blog): local fallback post $(date +%Y-%m-%d)"
      git push -q origin main || log "WARNING: push failed, will retry next run."
    fi
  fi
fi

# ---------- job 2: make the live site match the repo ----------
REPO_POSTS=$(find blog/posts -mindepth 1 -maxdepth 1 -type d | wc -l)
LIVE_POSTS=$(curl -fsS --max-time 30 "$SITE/sitemap.xml" 2>/dev/null | grep -c '<loc>' || echo 0)
log "posts in repo: $REPO_POSTS   posts live: $LIVE_POSTS"

if [ "$LIVE_POSTS" -ge "$REPO_POSTS" ]; then
  log "Live site is current. Nothing to deploy."
  exit 0
fi

log "Live site is behind by $((REPO_POSTS - LIVE_POSTS)) posts - deploying from here."
# CLOUDFLARE_HMW_BOT_TOKEN is the only token that works with wrangler Pages.
# The global key and CLOUDFLARE_TOKEN both fail with auth error 10000.
if CLOUDFLARE_API_TOKEN="${CLOUDFLARE_HMW_BOT_TOKEN:-}" \
   CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}" \
   npx --yes wrangler@latest pages deploy blog \
       --project-name=hmw-blog --commit-dirty=true >> "$LOG" 2>&1; then
  sleep 20
  AFTER=$(curl -fsS --max-time 30 "$SITE/sitemap.xml" 2>/dev/null | grep -c '<loc>' || echo 0)
  log "Deploy done. Posts live now: $AFTER (was $LIVE_POSTS)."
  [ "$AFTER" -lt "$REPO_POSTS" ] && log "WARNING: still behind after deploy - check the Pages project."
else
  log "ERROR: wrangler deploy failed. The blog is NOT publishing - fix the Cloudflare token."
fi
exit 0
