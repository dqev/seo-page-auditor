# SEO / AI-readability audit: https://example.com

**Score: 43/100** · Query: `example domain` · Final URL: https://example.com

Fetch extracted **25 words** (156 chars) from 201 chars cleaned HTML (raw source: 713 chars); 1 links. Search rank: **1**.
Raw H1: `[]` · AI-extracted H1: `[]`.

## Checks

### ✅ AI-extractable title
Fetch title: 'Example Domain'

### ❌ Title length 30–60 chars
Title is 14 chars: 'Example Domain'.
**Fix:** Rewrite title to 30–60 chars. Keep query near front. Current: 'Example Domain'.

### ❌ AI-visible H1
No H1 in raw HTML either — page truly has no H1.
**Fix:** Server-render one H1 containing the target query. If hero is client-rendered, move H1 to SSR HTML.

### ❌ Extracted body ≥300 words (not thin to AI)
Fetch extracted 25 words.
**Fix:** Expand real content to ≥300 words of extracted text (not nav/footer): answer the query, add steps/examples/FAQ. Re-run audit to confirm word count rises.

### ❌ Meta description present
Meta description: ''.
**Fix:** Add <meta name="description" content="...query-led 140–160 chars...">. Controls the search snippet.

### ✅ Images have alt text
No <img> in raw HTML.

### ❌ Structured data (JSON-LD)
No application/ld+json in raw HTML (Fetch extraction also drops it — AI can't see entities).
**Fix:** Add JSON-LD (Article/Product/FAQ/Breadcrumb as fitting) so AI answers can cite entities correctly.

### ❌ Canonical tag
No rel=canonical in raw HTML.
**Fix:** Add <link rel="canonical" href="<preferred URL>"> to consolidate ranking signals.

### ❌ Open Graph tags (link previews / AI citations)
No og:* tags in raw HTML (Fetch strips head tags, so AI citations fall back to title-only).
**Fix:** Add og:title/description/image + twitter:card so shares and AI citations render correctly.

### ✅ html lang attribute
lang='en' (raw HTML).

### ❌ Outbound/internal link graph
Fetch links: 1 (internal≈0, external≈1).
**Fix:** Add ≥3 contextual internal links to related pages with descriptive anchors; link out to 1–2 authoritative sources.

### ✅ Content in initial HTML (not JS-only)
Extracted 156 chars from 201 chars HTML (ratio 0.78).

### ✅ Indexed & ranking for query (pos 1)
Query 'example domain' → https://www.example.com/ at position 1. Snippet: 'Example Domain. This domain is for use in documentation examples without needing permission. Avoid use in operations. Learn more.'.

### ✅ Query terms in snippet/title/H1
All key terms ['example', 'domain'] appear in title/snippet/body.

## Fix today (priority order)

1. Rewrite title to 30–60 chars. Keep query near front. Current: 'Example Domain'.
2. Server-render one H1 containing the target query. If hero is client-rendered, move H1 to SSR HTML.
3. Expand real content to ≥300 words of extracted text (not nav/footer): answer the query, add steps/examples/FAQ. Re-run audit to confirm word count rises.
4. Add <meta name="description" content="...query-led 140–160 chars...">. Controls the search snippet.
5. Add JSON-LD (Article/Product/FAQ/Breadcrumb as fitting) so AI answers can cite entities correctly.
6. Add <link rel="canonical" href="<preferred URL>"> to consolidate ranking signals.
7. Add og:title/description/image + twitter:card so shares and AI citations render correctly.
8. Add ≥3 contextual internal links to related pages with descriptive anchors; link out to 1–2 authoritative sources.

---
*Audited live with TinyFish Search + Fetch.*
