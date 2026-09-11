# HMW — Grief Ritual Funnel: Handoff

Written for a fresh Claude Code session with local secrets. Nothing below assumes
prior conversation context. Repo: `howmindswork/hmw-blog`.

**Branch: `claude/grief-ritual-ad-copy-a36925`** — 2 commits, pushed, NOT merged.
Check it out before starting. `git log --oneline main..claude/grief-ritual-ad-copy-a36925`

---

## Business context

- Product: "Step-by-Step Ritual to Process Grief and Release Pain" — $97, on Gumroad
  (`lukeisthere.gumroad.com/l/EmotionalCompletionGuide`). 400+ sales, 1 refund ever.
- Free lead magnet: Star Feeding / Stone Release Ritual audio. Already hosted at
  `blog/assets/star-feeding-ritual.mp3`. Gumroad slug `StoneReleaseRitualAudio`.
- Order bump candidate: The Wanting Protocol (`gumroad.com/l/wanting`).
- Continuity: Skool, $9/mo for first 50 members —
  https://www.skool.com/how-minds-work-community-8311/about
- Traffic: IG, Threads, FB, TikTok, X, YouTube. Face reels with on-screen text; a
  local pipeline round-robins ~100 videos and overlays the text. That pipeline exists
  and works — do not rebuild it.
- Site: Cloudflare Pages, project `hmw-blog`, serves the `blog/` directory.
  **`.github/workflows/deploy.yml` only fires on push to `main`.**

### Existing Cloudflare Workers (found referenced in the repo)
| Worker | Purpose |
|---|---|
| `star-audio-capture.howmindswork.workers.dev` | Email capture for the free audio |
| `hmw-analytics.howmindswork.workers.dev` | Pageview/click tracking |
| `hmw-email-sequence.howmindswork.workers.dev` | Daily email sequence (cron 14:00 UTC) |
| `caoineadhanamaprotocol.howmindswork.workers.dev` | Self-hosted checkout — **copy this pattern** |
| `thewanting.howmindswork.workers.dev` | Self-hosted checkout — **copy this pattern** |

---

## Already done and pushed on this branch

1. **`content/ad-copy/grief-ritual/bank.md`** — 10 ad-copy variations (on-screen text +
   caption) for the $97 offer. Each carries its ANGLE and a real CITATION.
   These are now **style exemplars for a generator**, not a daily rotation.
2. **`scripts/daily_ad_copy.py`** — stdlib-only, date-deterministic picker over the bank.
   `--list`, `--all`, `--id V03`, `--date`. Writes `out/ad-copy/`, appends to the
   Actions job summary, optional POST to `AD_COPY_WEBHOOK_URL`.
3. **`.github/workflows/ad-copy-cron.yml`** — daily 12:00 UTC + manual dispatch.
4. **`scripts/wire_capture.py`** — idempotent site-wide wiring, already applied.

### Verified finding that drove #4
The star-audio popup (`blog/assets/popup-star-audio.js`), its capture worker, and the
hosted mp3 all existed — and **no page loaded the script.** Zero email capture
site-wide. Fixed on this branch:

- popup added to **182 / 185** pages (the 3 sales pages are deliberately excluded — a
  free-audio opt-in there trades a $97 decision for an email address)
- analytics added to 104 pages → now **185 / 185**
- **16** CTAs reading "Get the free audio" pointed at the $97 guide; repointed to
  `StoneReleaseRitualAudio`

Re-run `python3 scripts/wire_capture.py` after adding new posts. It's idempotent.

---

## TODO, in ROI order

### 1. Merge and verify capture end-to-end — DO FIRST
Nothing above is live until this branch hits `main`. Then submit a real email through
the popup and confirm: the audio actually arrives, and the address lands in whatever
`hmw-email-sequence` reads. **If `star-audio-capture` is dead, the popup is now
harvesting addresses into a void on 182 pages.** This was never verified from the
cloud session — no access to the Worker. Verify before driving traffic.

### 2. Self-hosted checkout for the $97, replacing Gumroad
Clone the `thewanting` Worker pattern. Requirements:
- Stripe Checkout at $97. Use a **restricted key** scoped to checkout-session
  creation, not the live secret key.
- Order bump on the payment page: The Wanting Protocol, and/or Skool $9 founding member.
- Must be **same-origin with the landing page** — `blog/assets/hmw-track.js` persists
  first-touch UTM attribution in localStorage, which is per-origin. Same-origin is the
  only way attribution survives landing → checkout. The script's header comment says
  this explicitly.
- Then sweep the **58** `EmotionalCompletionGuide` Gumroad links to the new URL. Use
  the same approach as `scripts/wire_capture.py`.

Why this is #2: Gumroad's cut on 400+ sales is roughly $3,800, and there is currently
no mechanism to offer a bump at all.

### 3. Daily ad-copy GENERATOR (replaces the fixed bank rotation)
**This was NOT built. Design only.** 5 posts/day cannot come from 10 fixed variations.

- Reuse the provider-fallback in `scripts/generate_post.py` → `_build_providers()`
  (Gemini → Cerebras → Groq → OpenRouter, ~20 rotating key names). Import it; do not
  duplicate that rotation logic.
- Build `content/ad-copy/grief-ritual/anchors.json`: a pool of **real, citable research
  anchors**. The generator varies the *angle* on a real anchor rather than inventing
  studies. ~24 anchors × 2-3 angles ≈ 50-70 variations before repeat.
- Seed anchors already proven in `bank.md`: Norton & Gino 2014 (JEP:General, rituals
  work on non-believers); Briñol et al. 2013 (Psych Science, physically discarding a
  written thought); Freud 1917 vs. his 1929 Binswanger letter vs. Klass/Silverman/
  Nickman 1996 Continuing Bonds; Wortman & Silver 1989 (the 5 stages were never
  validated for the bereaved); O'Connor, *The Grieving Brain* 2022; Wittstein et al.
  2005 NEJM (takotsubo — **the real Johns Hopkins paper**); DSM-5-TR 2022 Prolonged
  Grief Disorder; Volkan 1972 (linking objects); Pennebaker & Beall 1986; EMDR's
  pseudoscience-to-WHO-endorsement arc.
- Worth adding: Lieberman et al. 2007 (UCLA, affect labeling reduces amygdala
  response — this is the direct neuroscience for "say the memory out loud"); Doka 1989
  disenfranchised grief; Stroebe & Schut 1999 dual process model; Bonanno 2004
  resilience; Worden's four tasks.
- Keep a usage ledger so the same anchor doesn't fire twice in a week.

**Hard constraint for the generator's system prompt:** no invented studies, no invented
statistics, no sacred practice attributed to a named living tribe. The original viral
post claimed a 2019 Johns Hopkins PTSD trial with 73%/81%/6x figures and a Lakota
ritual called "Wičháȟpi Wóyute." None of that is real. It's a paid health product, so
that's FTC substantiation exposure, Meta/TikTok health-misinformation enforcement, and
the highest-velocity dogpile format on IG/TikTok. The account is the asset; a ban is
total revenue loss. Every variation in `bank.md` hits the same psychological triggers
on real citations — match that standard.

### 4. Email gate + sequence
Popup is live post-merge. Sequence work: capture → deliver audio → nurture → $97.
`hmw-email-sequence` already runs daily at 14:00 UTC; extend rather than rebuild.

---

## Secrets needed (names, for GitHub Actions or local)
`STRIPE_SECRET_KEY` (restricted), `RESEND_API_KEY`, `CLOUDFLARE_API_TOKEN` +
`CLOUDFLARE_ACCOUNT_ID` (both already in Actions), plus the existing
`GEMINI_API_KEY_BLOG` / `GROQ_API_KEY*` set for the generator.

Keep money credentials separate from content credentials. A runaway copy generator
should be able to waste tokens, never to touch revenue or the list.

---

## Do NOT do
- **Don't rebuild the video pipeline.** It exists locally and works.
- **Don't rewrite the $97 PDF.** 400+ sales, 1 refund. Don't touch what converts.
- **Don't post the same 10 variations daily.** Near-duplicate content from one account
  gets suppressed on IG and TikTok. Ship item 3 first.

## Assets the user has, not in the repo
Two product images (audio/ear artwork → free audio; stones-and-river collage → $97
guide), `Guided_Stone_Release_Ritual_Audio_1.mp3`, `Emotional_completion_guide_3.pdf`,
a Wičháȟpi Wóyute book on Gumroad, and an 81-page audiobook. Collect these locally
before building landing pages.
