# HMW Blog Content Style Guide

## Typography Rules

### Hyphens & Dashes - CRITICAL

**NEVER use em dashes (—) or en dashes (–) anywhere in the blog.**

- ✅ Correct: `word - word` or `word: phrase` or `word; phrase`
- ❌ Wrong: `word—word` or `word–word` (em dash or en dash)

Use only ASCII hyphen-minus (-) with spaces around it: ` - `

**Why:** Em dashes cause character encoding issues across different systems and browsers. They're inconsistent with the HMW brand and create character width problems in responsive layouts.

## Examples

Before (WRONG):
```
Learn the exact ritual—it works.
Protection—here's how.
```

After (CORRECT):
```
Learn the exact ritual - it works.
Protection - here's how.
```

## Automated Check

Before committing content, search the file for the em dash character (U+2013, U+2014):
```bash
grep "—" file.html
```

If you find any, replace with: ` - ` (space-hyphen-space)

---

**Last updated:** 2026-05-06
