# Bulk stress test — 56 diverse sites

One command each, live pages, never stopped on error: `python batch.py <start> <end>` (see `sites.txt`, `batch.py`).

55/56 audited cleanly. Only failure: `httpstat.us/404` → clean `page_not_found` error exit (correct behavior).
Zero crashes, zero hangs. Score range 43–93, median 71 — no inflation: minimal pages (git-scm, nginx.org) score low, rich docs (docker, MDN) score high.

## All scores

| score | url | words | rank |
|---|---|---|---|
| 93 | https://www.docker.com | 385 | 1 |
| 87 | https://stripe.com | 1106 | 1 |
| 87 | https://www.mongodb.com | 891 | 1 |
| 86 | https://developer.mozilla.org/en-US/docs/Web/HTML | 1074 | 1 |
| 86 | https://www.typescriptlang.org | 684 | 1 |
| 86 | https://linear.app | 953 | 1 |
| 86 | https://techcrunch.com | 873 | 1 |
| 86 | https://css-tricks.com | 351 | 1 |
| 86 | https://www.smashingmagazine.com | 1127 | 1 |
| 86 | https://en.wikipedia.org/wiki/Python_(programming_language) | 12480 | 1 |
| 86 | https://www.shopify.com | 498 | 1 |
| 86 | https://www.postgresql.org | 899 | 1 |
| 86 | https://www.spiegel.de | 727 | 1 |
| 79 | https://github.com | 436 | 1 |
| 79 | https://nodejs.org/en | 280 | 1 |
| 79 | https://www.figma.com | 225 | 1 |
| 79 | https://pypi.org | 81 | 1 |
| 79 | https://www.bbc.com/news | 1178 | 1 |
| 79 | https://www.theverge.com | 2566 | 1 |
| 79 | https://www.samsung.com | 161 | 1 |
| 79 | https://www.nasa.gov | 336 | 1 |
| 73 | https://react.dev | 910 | 1 |
| 71 | https://kubernetes.io | 494 | 3 |
| 71 | https://tailwindcss.com | 802 | 1 |
| 71 | https://web.dev | 929 | 1 |
| 71 | https://redis.io | 158 | 1 |
| 71 | https://hi.wikipedia.org/wiki/भारत | 13726 | 1 |
| 71 | https://openai.com | 171 | 1 |
| 67 | https://www.uber.com | 486 | 1 |
| 64 | https://vercel.com | 120 | 1 |
| 64 | https://www.nytimes.com | 481 | 1 |
| 64 | https://www.ted.com/talks | 246 | 1 |
| 64 | https://www.amazon.com | 743 | 1 |
| 64 | https://www.ebay.com | 119 | 1 |
| 64 | https://www.apple.com | 118 | 1 |
| 64 | https://www.ikea.com | 69 | 1 |
| 64 | https://www.booking.com | 181 | 1 |
| 64 | https://www.lemonde.fr | 198 | 1 |
| 64 | https://www.anthropic.com | 213 | 1 |
| 64 | https://huggingface.co | 379 | 1 |
| 60 | https://www.python.org | 232 | 1 |
| 60 | https://www.x.com | 72 | 1 |
| 57 | https://stackoverflow.com | 771 | 1 |
| 57 | https://caniuse.com | 191 | 1 |
| 57 | https://dev.to | 428 | 1 |
| 57 | https://www.instagram.com | 28 | 1 |
| 54 | https://www.notion.so | 132 | None |
| 50 | https://www.npmjs.com | 154 | 1 |
| 50 | https://news.ycombinator.com | 743 | 1 |
| 50 | https://www.etsy.com | 287 | 1 |
| 50 | https://www.airbnb.com | 75 | 1 |
| 50 | https://arxiv.org | 616 | 1 |
| 43 | https://git-scm.com | 74 | 1 |
| 43 | https://nginx.org | 210 | 1 |
| 43 | https://www.baidu.com | 39 | 1 |

Raw per-site JSON: `bulk/<n>.json` (n = line number in `sites.txt`). Aggregate: `bulk/results-*.jsonl`.
