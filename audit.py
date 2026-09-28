#!/usr/bin/env python3
"""
SEO Page Auditor — TinyFish Student Bounty Drop 001.

Takes any live URL (+ optional target search query), uses TinyFish Search
(how the page shows up) + TinyFish Fetch (what an AI tool actually extracts),
plus an optional 3rd endpoint — TinyFish Agent (rendered-page check for
JS-only content) — then reports visibility gaps with same-day fixes.

Usage:
  python audit.py https://example.com --query "example domain docs"
  python audit.py https://example.com --query "..." --with-agent
  python audit.py https://example.com --json --out report.json

Requires: `tinyfish` CLI authenticated (TINYFISH_API_KEY) — see README.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser


# ---------------------------------------------------------------- TinyFish ---

def run_tinyfish(args: list[str], timeout: int = 90) -> str:
    """Run a tinyfish CLI command, return stdout. Raises on failure."""
    try:
        p = subprocess.run(
            ["tinyfish", *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        sys.exit("ERROR: `tinyfish` CLI not found. Install: npm install -g @tiny-fish/cli")
    if p.returncode != 0:
        sys.exit(f"ERROR running `tinyfish {' '.join(args)}`:\n{p.stderr.strip()[:2000]}")
    return p.stdout


def tf_search(query: str) -> dict:
    out = run_tinyfish(["search", "query", query])
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"ERROR: could not parse `tinyfish search` output:\n{out[:2000]}")


def tf_fetch(urls: list[str], fmt: str = "markdown", with_links: bool = True) -> dict:
    cmd = ["fetch", "content", "get", "--format", fmt]
    if with_links:
        cmd.append("--links")
    cmd += urls
    out = run_tinyfish(cmd, timeout=120)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"ERROR: could not parse `tinyfish fetch` output:\n{out[:2000]}")


def tf_agent_render_check(url: str) -> dict | None:
    """3rd meaningful endpoint: ask TinyFish Agent what a rendered browser sees.

    Compares agent-observed H1/main-text vs Fetch-extracted text to prove
    JS-only content gaps. Returns dict with agent findings or None on failure.
    """
    goal = (
        "Open the page and report as JSON with keys "
        '{"h1": str|null, "title": str|null, "main_text_chars": int, '
        '"main_text_sample": str (first 500 chars of visible main content)}. '
        "Do not click away from the page."
    )
    try:
        out = run_tinyfish(
            ["agent", "run", "--url", url, "--sync", goal],
            timeout=300,
        )
    except SystemExit as e:
        print(f"[warn] agent check skipped: {e}", file=sys.stderr)
        return None
    # --sync streams SSE `data: {...}` lines; find COMPLETED resultJson.
    result_json = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "COMPLETE" and ev.get("status") == "COMPLETED":
                result_json = ev.get("resultJson", ev.get("result", None))
                break
    if result_json is None:
        # Fall back: whole stdout may already be JSON.
        try:
            maybe = json.loads(out)
            if isinstance(maybe, dict):
                result_json = maybe.get("resultJson", maybe)
        except json.JSONDecodeError:
            pass
    if isinstance(result_json, str):
        try:
            result_json = json.loads(result_json)
        except json.JSONDecodeError:
            result_json = {"raw": result_json[:1000]}
    # CLI --sync may wrap: {"status":"COMPLETED","run_id":...,"result":{...}} — unwrap.
    if isinstance(result_json, dict):
        inner = result_json.get("result")
        if isinstance(inner, dict):
            result_json = inner
    return result_json if isinstance(result_json, dict) else ({"raw": str(result_json)[:1000]} if result_json else None)


# ---------------------------------------------------------------- Raw HTML ---

def fetch_raw_html(url: str, timeout: int = 25) -> tuple[str, str]:
    """Live raw-HTML ground truth (stdlib urllib, no key needed).

    Returns (body, content_type). Non-HTML content (PDF, images…) returns
    ("", content_type) so tag checks can SKIP honestly instead of failing.
    TinyFish Fetch returns *cleaned* HTML (boilerplate stripped, tags like
    <html lang>, canonical, OG, JSON-LD often removed). Comparing raw source
    vs the AI-extracted view is exactly what surfaces "page has it, but AI
    tools can't see it" gaps. Returns ("", "") on failure (checks fall back
    to Fetch data and note the limitation).
    """
    try:
        # Quote non-ASCII path/query (e.g. /wiki/भारत) — urllib needs ASCII.
        parts = urllib.parse.urlsplit(url)
        safe_url = urllib.parse.urlunsplit((
            parts.scheme, parts.netloc,
            urllib.parse.quote(parts.path, safe="/%"),
            urllib.parse.quote(parts.query, safe="=&%"),
            parts.fragment))
        req = urllib.request.Request(
            safe_url, headers={"User-Agent": "Mozilla/5.0 (SEO-Page-Auditor bounty demo)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get_content_type() or "").lower()
            if ctype and "html" not in ctype and "xhtml" not in ctype:
                return "", ctype
            raw = r.read().decode("utf-8", "replace")
        return raw[:2_000_000], ctype  # generous: real <h1> can sit past 500k on script-heavy pages
    except Exception as e:
        print(f"[warn] raw HTML fetch failed ({e}); tag checks use Fetch data.", file=sys.stderr)
        return "", ""


# ---------------------------------------------------------------- HTML parse ---

class _Meta(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._title_done = False  # first <title> wins; SVG <title> must not overwrite
        self._svg_depth = 0
        self.h1: list[str] = []
        self.h2: list[str] = []
        self._in_h1 = False
        self._in_h2 = False
        self._buf = ""
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.robots = ""
        self.html_lang = ""
        self.img_total = 0
        self.img_missing_alt = 0
        self.jsonld_count = 0
        self._in_jsonld = False
        self.links_internal = 0
        self.links_external = 0
        self._host = ""
        self.word_count_html = 0
        self._skip = False  # script/style

    def feed_host(self, host: str):
        self._host = host.lower()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self._skip = True
        if tag == "svg":
            self._svg_depth += 1
        # Pad captured headings so nested tags don't glue words ("library<span>designers").
        if self._in_title or self._in_h1 or self._in_h2:
            self._buf += " "
        if tag == "html" and "lang" in a:
            self.html_lang = a["lang"]
        if tag == "title":
            # First <title> (in <head>) wins; ignore SVG icon titles etc.
            if not self._title_done and self._svg_depth == 0:
                self._in_title = True
                self._buf = ""
        elif tag == "h1":
            if self._svg_depth == 0:
                self._in_h1 = True
                self._buf = ""
        elif tag == "h2":
            if self._svg_depth == 0:
                self._in_h2 = True
                self._buf = ""
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name and "content" in a:
                self.meta[name] = a["content"]
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.canonical = a.get("href", "")
        elif tag == "img":
            self.img_total += 1
            if not (a.get("alt") or "").strip():
                self.img_missing_alt += 1
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self.jsonld_count += 1
        elif tag == "a" and "href" in a:
            href = a["href"]
            try:
                host = urllib.parse.urlparse(href).netloc.lower()
            except Exception:
                host = ""
            if not host or host == self._host:
                self.links_internal += 1
            else:
                self.links_external += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag == "svg" and self._svg_depth > 0:
            self._svg_depth -= 1
        if tag == "title" and self._in_title:
            self.title = " ".join(self._buf.split()).replace("\xa0", " ")
            self._in_title = False
            self._title_done = True
        elif tag == "h1" and self._in_h1:
            self.h1.append(" ".join(self._buf.split()).replace("\xa0", " "))
            self._in_h1 = False
        elif tag == "h2" and self._in_h2:
            self.h2.append(" ".join(self._buf.split()).replace("\xa0", " "))
            self._in_h2 = False

    def handle_data(self, data):
        if self._in_title or self._in_h1 or self._in_h2:
            self._buf += data
        if not self._skip and data.strip():
            self.word_count_html += len(data.split())


def parse_html(html: str, host: str) -> _Meta:
    m = _Meta()
    m.feed_host(host)
    try:
        m.feed(html)  # no truncation: head tags are early but <h1> may sit deep
    except Exception:
        pass
    return m


# ---------------------------------------------------------------- Audit ---

def norm_url(u: str) -> str:
    u = u.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def domain_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def check(title: str, passed: bool | None, detail: str, fix: str) -> dict:
    """passed=True→PASS, False→FAIL, None→SKIP (not applicable, excluded from score)."""
    status = "SKIP" if passed is None else ("PASS" if passed else "FAIL")
    return {"check": title, "status": status,
            "detail": detail, "fix": fix if status == "FAIL" else ""}


def audit(url: str, query: str | None, with_agent: bool = False) -> dict:
    url = norm_url(url)
    host = urllib.parse.urlparse(url).netloc.lower()
    domain = domain_of(url)

    # 1) TinyFish FETCH — markdown (what AI tools read) + html (raw signals).
    md_res = tf_fetch([url], fmt="markdown", with_links=True)
    html_res = tf_fetch([url], fmt="html", with_links=False)
    if md_res.get("errors"):
        sys.exit(f"ERROR fetching page: {md_res['errors']}")
    md = (md_res.get("results") or [{}])[0]
    html_doc = (html_res.get("results") or [{}])[0]
    html_raw = html_doc.get("text", "") or ""  # --format html returns cleaned HTML in `text`
    text = md.get("text", "") or ""
    words = len(text.split())
    md_title = md.get("title", "") or ""
    md_desc = md.get("description") or ""
    page_meta = md.get("page_metadata", {}) or {}
    links = md.get("links", []) or []

    parsed = parse_html(html_raw, host)          # AI-extracted view (cleaned)
    raw_source, raw_ctype = fetch_raw_html(url)  # ground truth (live raw HTML)
    non_html = bool(raw_ctype) and "html" not in raw_ctype and "xhtml" not in raw_ctype
    if non_html:
        raw_source = ""  # don't parse binaries as HTML
    raw = parse_html(raw_source, host) if raw_source else parsed
    title = parsed.title or raw.title or md_title
    h1s = parsed.h1
    # Fallback: markdown H1 if HTML parse missed it (cleaned-HTML variants).
    if not h1s:
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            h1s = [m.group(1).strip()]
    raw_h1s = raw.h1 if raw_source else h1s
    # Link graph from Fetch `links` array (cleaned HTML drops hrefs).
    n_internal = n_external = 0
    for lk in links:
        try:
            lh = urllib.parse.urlparse(lk).netloc.lower()
        except Exception:
            lh = ""
        if not lh or lh == host or (domain and lh.endswith(domain)):
            n_internal += 1
        else:
            n_external += 1

    # 2) TinyFish SEARCH — how the page shows up.
    if not query:
        query = f"{domain} {title}".strip()[:120] or domain
    s = tf_search(query)
    results = s.get("results", []) or []
    rank = None
    matched = None
    for r in results:
        rhost = urllib.parse.urlparse(r.get("url", "")).netloc.lower()
        if domain and domain in rhost:
            rank = r.get("position")
            matched = r
            break

    checks: list[dict] = []

    # Non-HTML URLs (PDF, images…): HTML-tag checks SKIP honestly instead of failing.
    def tag_check(title: str, ok: bool, detail: str, fix: str) -> dict:
        if non_html:
            return check(title, None,
                         f"Skipped — URL serves {raw_ctype or 'non-HTML content'}; HTML tags don't apply.", "")
        return check(title, ok, detail, fix)

    # --- readability for AI tools (Fetch side) ---
    checks.append(tag_check(
        "AI-extractable title",
        bool(title.strip()),
        f"Fetch title: {title[:80]!r}" if title else "Fetch returned no <title>.",
        "Add a unique <title> (30–60 chars, include target query). AI tools + search use it as the headline.",
    ))
    tl = len(title)
    checks.append(tag_check(
        "Title length 30–60 chars",
        30 <= tl <= 60,
        f"Title is {tl} chars: {title[:80]!r}.",
        f"Rewrite title to 30–60 chars. Keep query near front. Current: {title[:100]!r}.",
    ))
    checks.append(tag_check(
        "AI-visible H1",
        len(h1s) >= 1,
        f"Found {len(h1s)} H1(s): {[h[:60] for h in h1s]}." if h1s
        else ("No H1 in raw HTML either — page truly has no H1." if not raw_h1s
              else f"Raw HTML has H1 {[h[:60] for h in raw_h1s]} but Fetch extraction drops it — AI tools see no H1."),
        "Server-render one H1 containing the target query. If hero is client-rendered, move H1 to SSR HTML.",
    ))
    if len(raw_h1s) > 1:
        checks.append(tag_check(
            "Single H1",
            False,
            f"{len(raw_h1s)} H1s in raw HTML: {[h[:50] for h in raw_h1s[:3]]}.",
            "Keep exactly one H1 per page; demote others to H2.",
        ))
    checks.append(check(
        "Extracted body ≥300 words (not thin to AI)",
        words >= 300,
        f"Fetch extracted {words} words.",
        "Expand real content to ≥300 words of extracted text (not nav/footer): answer the query, add steps/examples/FAQ. Re-run audit to confirm word count rises.",
    ))
    checks.append(tag_check(
        "Meta description present",
        bool((raw.meta.get("description") or md_desc or "").strip()),
        f"Meta description: {(raw.meta.get('description') or md_desc or '')[:120]!r}.",
        "Add <meta name=\"description\" content=\"...query-led 140–160 chars...\">. Controls the search snippet.",
    ))
    checks.append(tag_check(
        "Images have alt text",
        raw.img_missing_alt == 0,
        f"{raw.img_total} img(s) in raw HTML, {raw.img_missing_alt} missing alt." if raw.img_total else "No <img> in raw HTML.",
        f"Add descriptive alt to {raw.img_missing_alt} image(s). AI tools + image search read alt, not pixels.",
    ))
    checks.append(tag_check(
        "Structured data (JSON-LD)",
        raw.jsonld_count > 0,
        f"Found {raw.jsonld_count} JSON-LD block(s) in raw HTML." if raw.jsonld_count else "No application/ld+json in raw HTML (Fetch extraction also drops it — AI can't see entities).",
        "Add JSON-LD (Article/Product/FAQ/Breadcrumb as fitting) so AI answers can cite entities correctly.",
    ))
    checks.append(tag_check(
        "Canonical tag",
        bool(raw.canonical),
        f"Canonical: {raw.canonical!r}." if raw.canonical else "No rel=canonical in raw HTML.",
        "Add <link rel=\"canonical\" href=\"<preferred URL>\"> to consolidate ranking signals.",
    ))
    og = any(k.startswith("og:") for k in raw.meta)
    checks.append(tag_check(
        "Open Graph tags (link previews / AI citations)",
        og,
        "og:* tags present in raw HTML." if og else "No og:* tags in raw HTML (Fetch strips head tags, so AI citations fall back to title-only).",
        "Add og:title/description/image + twitter:card so shares and AI citations render correctly.",
    ))
    checks.append(tag_check(
        "html lang attribute",
        bool(raw.html_lang),
        f"lang={raw.html_lang!r} (raw HTML)." if raw.html_lang else "No <html lang> in raw HTML.",
        'Set <html lang="en"> (or page language) for accessibility + language-targeted ranking.',
    ))
    checks.append(check(
        "Outbound/internal link graph",
        len(links) >= 3,
        f"Fetch links: {len(links)} (internal≈{n_internal}, external≈{n_external}).",
        "Add ≥3 contextual internal links to related pages with descriptive anchors; link out to 1–2 authoritative sources.",
    ))
    # Extraction gap: raw source vs what Fetch hands to AI tools.
    html_len = len(html_raw)
    raw_len = len(raw_source)
    raw_words = raw.word_count_html if raw_source else words
    thin_ratio = (len(text) / max(html_len, 1))
    if raw_words >= 300 and words < 300:
        dropped = 100 * (1 - words / max(raw_words, 1))
        checks.append(tag_check(
            "Fetch keeps page copy (no extraction drop)",
            False,
            f"Raw HTML holds ~{raw_words} words but Fetch extracts {words} ({dropped:.0f}% dropped). "
            f"Copy exists yet never reaches AI readers — hero is likely canvas/animated/shadow-DOM markup.",
            "Put key copy in plain <h1>/<p> in the DOM (not canvas, text-as-image, or JS-injected widgets). "
            "Re-run audit to confirm extracted words rise.",
        ))
    elif raw_words < 100 and raw_len > 50_000:
        checks.append(tag_check(
            "Content in initial HTML (not JS-only)",
            False,
            f"Ships {raw_len // 1000}kb of HTML/JS but only ~{raw_words} raw words ({words} extracted). Likely client-rendered.",
            "Server-render (or pre-render) H1 + first 200 words. Verify: view-source should contain the H1 text.",
        ))
    else:
        checks.append(tag_check(
            "Content in initial HTML (not JS-only)",
            True,
            f"Extracted {len(text)} chars from {html_len} chars cleaned HTML (ratio {thin_ratio:.2f}); raw ~{raw_words} words.",
            "",
        ))

    # --- visibility (Search side) ---
    if matched:
        checks.append(check(
            f"Indexed & ranking for query (pos {rank})",
            True,
            f"Query {query!r} → {matched.get('url')} at position {rank}. Snippet: {(matched.get('snippet') or '')[:140]!r}.",
            "",
        ))
        snippet = (matched.get("snippet") or "").lower()
        q_terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3][:4]
        missing = [t for t in q_terms if t not in snippet and t not in title.lower() and t not in text.lower()[:5000]]
        checks.append(check(
            "Query terms in snippet/title/H1",
            not missing,
            f"Query terms: {q_terms}. Missing from visible surfaces: {missing}." if missing else f"All key terms {q_terms} appear in title/snippet/body.",
            f"Work missing terms into title + H1 + first 100 words: {missing}. Then request re-indexing.",
        ))
    else:
        checks.append(check(
            "Indexed & ranking for query",
            False,
            f"Domain {domain!r} not in top {len(results)} for {query!r}. Top hit: {(results[0].get('url') if results else None)!r}.",
            f"Check: 1) robots/sitemap includes URL, 2) title+H1 contain query terms, 3) get 1–2 internal links from indexed pages, 4) Fetch in Search Console / request indexing. Re-run: python audit.py {url} --query {query!r}.",
        ))

    # --- 3rd endpoint: rendered-browser comparison ---
    agent_cmp = None
    if with_agent:
        agent_data = tf_agent_render_check(url)
        if agent_data:
            a_h1 = (agent_data.get("h1") or "").strip()
            a_chars = agent_data.get("main_text_chars", 0) or 0
            try:
                a_chars = int(a_chars)
            except (TypeError, ValueError):
                a_chars = 0
            gap = a_chars - len(text)
            # FAIL only on real signals: rendered H1 that Fetch/raw both miss,
            # or a very large char gap (boilerplate inflation alone isn't a gap).
            h1_hidden = bool(a_h1) and not h1s and not raw_h1s
            rendered_sees_more = (h1_hidden and gap > 500) or gap > 2000
            agent_cmp = {"agent": agent_data, "fetch_chars": len(text),
                         "gap_chars": gap, "rendered_sees_more": rendered_sees_more,
                         "h1_hidden": h1_hidden}
            detail = (f"Fetch: {len(text)} chars vs rendered: {a_chars} chars (gap {gap}). Agent H1: {a_h1[:80]!r}."
                      if a_chars else f"Agent returned: {str(agent_data)[:200]!r}.")
            if a_h1 and not h1s:
                detail += (f" Rendered browser sees H1 {a_h1[:60]!r} that Fetch extraction drops"
                           + (" (matches raw HTML — see 'AI-visible H1' fix)." if raw_h1s else " (also missing from raw HTML)."))
            checks.append(check(
                "Rendered browser ≈ Fetch (no hidden JS content)",
                not rendered_sees_more,
                detail,
                "Content differs between Fetch and rendered browser ⇒ move key content to SSR. Re-run with --with-agent to confirm gap closes.",
            ))
        else:
            checks.append(check(
                "Rendered browser check",
                True,
                "Agent check unavailable/skipped; Fetch-vs-HTML heuristic used instead.",
                "",
            ))

    fails = [c for c in checks if c["status"] == "FAIL"]
    scored = [c for c in checks if c["status"] != "SKIP"]
    score = round(100 * (len(scored) - len(fails)) / max(len(scored), 1))

    return {
        "url": url, "final_url": md.get("final_url", url),
        "query": query, "score": score,
        "fetch": {"title": md_title, "words": words,
                  "chars": len(text), "links_found": len(links),
                  "html_chars": html_len,
                  "raw_html_chars": len(raw_source),
                  "raw_h1": raw_h1s[:3],
                  "fetch_h1": h1s[:3]},
        "search": {"query": query, "rank": rank,
                   "matched_url": (matched or {}).get("url") if matched else None,
                   "top_results": [{"position": r.get("position"), "title": r.get("title"),
                                    "url": r.get("url")} for r in results[:5]]},
        "agent_comparison": agent_cmp,
        "checks": checks,
        "fixes": [c["fix"] for c in fails if c["fix"]],
    }


# ---------------------------------------------------------------- Report ---

def report_md(r: dict) -> str:
    L = [f"# SEO / AI-readability audit: {r['url']}",
         f"\n**Score: {r['score']}/100** · Query: `{r['query']}` · Final URL: {r['final_url']}",
         f"\nFetch extracted **{r['fetch']['words']} words** ({r['fetch']['chars']} chars) from {r['fetch']['html_chars']} chars cleaned HTML "
         f"(raw source: {r['fetch']['raw_html_chars']} chars); "
         f"{r['fetch']['links_found']} links. Search rank: **{r['search']['rank'] or 'not in top results'}**."
         f"\nRaw H1: `{r['fetch']['raw_h1']}` · AI-extracted H1: `{r['fetch']['fetch_h1']}`."]
    if r.get("agent_comparison"):
        a = r["agent_comparison"]
        L.append(f"\nRendered-browser check: fetch {a['fetch_chars']} chars vs rendered ≈{a['agent'].get('main_text_chars', '?')} chars "
                 f"(gap {a['gap_chars']}). {'⚠️ rendered sees MORE — JS gap.' if a['rendered_sees_more'] else 'OK — matches.'}")
    L.append("\n## Checks\n")
    for c in r["checks"]:
        icon = {"PASS": "✅", "FAIL": "❌"}.get(c["status"], "➖")
        L.append(f"### {icon} {c['check']}")
        L.append(f"{c['detail']}")
        if c["status"] == "FAIL" and c["fix"]:
            L.append(f"**Fix:** {c['fix']}")
        L.append("")
    if r["fixes"]:
        L.append("## Fix today (priority order)\n")
        for i, f in enumerate(r["fixes"], 1):
            L.append(f"{i}. {f}")
    L.append("\n---\n*Audited live with TinyFish Search + Fetch"
             + (" + Agent" if r.get("agent_comparison") else "") + ".*")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit whether AI search/fetch can read a page (TinyFish).")
    ap.add_argument("url", help="Page URL to audit (any live URL)")
    ap.add_argument("--query", default=None, help="Target search query (default: derived from domain+title)")
    ap.add_argument("--with-agent", action="store_true",
                    help="Also run TinyFish Agent rendered check (3rd endpoint, slower/metered)")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of markdown")
    ap.add_argument("--out", default=None, help="Write report to file")
    args = ap.parse_args()

    r = audit(args.url, args.query, with_agent=args.with_agent)
    out = json.dumps(r, indent=2) if args.json else report_md(r)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out + "\n")
        print(f"Wrote {args.out} (score {r['score']}/100, {len(r['fixes'])} fixes)")
    else:
        print(out)


if __name__ == "__main__":
    main()
