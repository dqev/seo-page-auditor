# SEO Page Auditor — TinyFish Bounty Drop 001

AI search is changing how pages get found. This tool checks whether AI
search and fetch tools can actually **read and understand** a page, and how
that ties to SEO and ranking.

## What it does

```
python audit.py <URL> [--query "target keywords"] [--with-agent] [--json] [--out report.md]
```

1. **TinyFish Fetch** the live URL twice — `markdown` (what an AI tool
   extracts: title, text, word count, links) + `html` (cleaned article HTML:
   which headings/body an AI actually sees).
2. **Raw-HTML ground truth** (live stdlib fetch) — parses the real
   `<title>`/meta/canonical/OG/JSON-LD/lang/H1/alt tags. The raw-vs-extracted
   comparison proves "page has it, but AI tools can't see it".
3. **TinyFish Search** the target query (or domain+title) — does the page
   show up, at what position, and do query terms appear in the snippet?
4. *(optional 3rd endpoint)* **TinyFish Agent** opens the page in a real
   browser and reports the rendered H1/main text. If the browser sees much
   more than Fetch, content is JS-only — a concrete AI-visibility bug.
5. Prints a scored report: what AI tools **can/can't read**, visibility
   gaps, and **same-day fixes** (exact tag to add, where, and how to verify).

## How TinyFish is used (bounty requirement 5)

| Endpoint | CLI call | Contributes |
|---|---|---|
| Search | `tinyfish search query "<query>"` | visibility: rank, snippet, query-term coverage |
| Fetch | `tinyfish fetch content get --format markdown --links <url>` + `--format html` | readability: extracted text vs raw HTML signals |
| Agent | `tinyfish agent run --url <url> --sync "<goal>"` (`--with-agent`) | proves JS-only gaps: rendered vs fetched text |

No saved copies — every run hits **live pages**. Search and Fetch both
shape the score; Agent adds the rendered comparison (3 endpoints = 200-pt
tier; without `--with-agent` it's Search+Fetch = 100-pt tier).

## Setup

```bash
npm install -g @tiny-fish/cli
export TINYFISH_API_KEY="<your-key-from-tinyfish-dashboard>"
python audit.py https://example.com --query "example domain"
```

## Demos (live pages)

```bash
python audit.py https://example.com --query "example domain" --out demo-example.md
python audit.py https://www.semrush.com/siteaudit/ --query "free seo audit tool" --out demo-semrush.md
python audit.py https://developers.google.com/search/blog/2018/02/seo-audit-category-in-lighthouse --query "lighthouse seo audit" --out demo-lighthouse.md
python audit.py https://reicon.dev --query "reicon free icons" --out demo-reicon.md
python audit.py https://devchauhan.in --query "Devpratap Chauhan" --out demo-portfolio.md
# with rendered check (metered, slower):
python audit.py https://devchauhan.in --query "Devpratap Chauhan" --with-agent --out demo-portfolio-agent.md
```

See `demo-*.md` reports for what AI tools can/can't read per page.

## What a site owner does same-day

Typical output: missing meta description → exact tag to paste;
no H1 in Fetch but present when rendered → move H1 to SSR and re-run
`python audit.py <url> --query "..."` to confirm the word-count/rank
checks flip to PASS.
