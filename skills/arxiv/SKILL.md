---
name: arxiv
description: Search, download, and summarize academic papers from arXiv. Use when user says "search arxiv", "download paper", "fetch arxiv", "arxiv search", "get paper pdf", or wants to find and save papers from arXiv to the local paper library.
argument-hint: [query-or-arxiv-id]
allowed-tools: Bash(*), Read, Write
---

# arXiv Paper Search & Download

Search topic or arXiv paper ID: $ARGUMENTS

## Constants

- **PAPER_DIR** - Local directory to save downloaded paper artifacts. Default: `papers/` in the current project directory.
- **MAX_RESULTS = 10** - Default number of search results.
- **ARXIV_FETCHER** — canonical name `arxiv_fetch.py`, resolved per
  [`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2
  (Policy D1 — primary + fallback cascade). If unresolved (canonical
  chain exhausted), fall back to the inline Python alternative
  documented in Step 2.

> Overrides (append to arguments):
> - `/arxiv "attention mechanism" - max: 20` - return up to 20 results
> - `/arxiv "2301.07041" - download` - download a specific paper's reading artifacts
> - `/arxiv "query" - dir: literature/` - save artifacts to a custom directory
> - `/arxiv "query" - download: all` - download reading artifacts for all results

## Workflow

### Step 1: Parse Arguments

Parse `$ARGUMENTS` for directives:

- **Query or ID**: main search term or a bare arXiv ID such as `2301.07041` or `cs/0601001`
- **`- max: N`**: override MAX_RESULTS (e.g., `- max: 20`)
- **`- dir: PATH`**: override PAPER_DIR (e.g., `- dir: literature/`)
- **`- download`**: download the first result's reading artifacts after listing
- **`- download: all`**: download reading artifacts for all results

By default, a download now means:
- PDF
- source archive from `https://arxiv.org/src/<id>` when available
- extracted source directory when extraction succeeds

If the argument matches an arXiv ID pattern (`YYMM.NNNNN` or `category/NNNNNNN`), skip the search and go directly to Step 3.

### Step 2: Search arXiv

Resolve `$ARXIV_FETCHER` via the canonical strict-safe chain (see
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2):

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
ARXIV_FETCHER=".aris/tools/arxiv_fetch.py"
[ -f "$ARXIV_FETCHER" ] || ARXIV_FETCHER="tools/arxiv_fetch.py"
[ -f "$ARXIV_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && ARXIV_FETCHER="$ARIS_REPO/tools/arxiv_fetch.py"; }
[ -f "$ARXIV_FETCHER" ] || ARXIV_FETCHER=""
```

**If `$ARXIV_FETCHER` is non-empty**, run:

```bash
python3 "$ARXIV_FETCHER" search "QUERY" --max MAX_RESULTS
```

**If `$ARXIV_FETCHER` is empty** (Policy D1 cascade), fall back to inline Python:

```bash
python3 - <<'PYEOF'
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2005/Atom"
query = urllib.parse.quote("QUERY")
url = (f"http://export.arxiv.org/api/query"
       f"?search_query={query}&start=0&max_results=MAX_RESULTS"
       f"&sortBy=relevance&sortOrder=descending")
with urllib.request.urlopen(url, timeout=30) as r:
    root = ET.fromstring(r.read())
papers = []
for entry in root.findall(f"{{{NS}}}entry"):
    aid = entry.findtext(f"{{{NS}}}id", "").split("/abs/")[-1].split("v")[0]
    title = (entry.findtext(f"{{{NS}}}title", "") or "").strip().replace("\n", " ")
    abstract = (entry.findtext(f"{{{NS}}}summary", "") or "").strip().replace("\n", " ")
    authors = [a.findtext(f"{{{NS}}}name", "") for a in entry.findall(f"{{{NS}}}author")]
    published = entry.findtext(f"{{{NS}}}published", "")[:10]
    cats = [c.get("term", "") for c in entry.findall(f"{{{NS}}}category")]
    papers.append({
        "id": aid,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "categories": cats,
        "pdf_url": f"https://arxiv.org/pdf/{aid}.pdf",
        "abs_url": f"https://arxiv.org/abs/{aid}",
    })
print(json.dumps(papers, ensure_ascii=False, indent=2))
PYEOF
```

Present results as a table:

```text
| # | arXiv ID   | Title               | Authors        | Date       | Category |
|---|------------|---------------------|----------------|------------|----------|
| 1 | 2301.07041 | Attention Is All... | Vaswani et al. | 2017-06-12 | cs.LG    |
```

### Step 3: Fetch Details for a Specific ID

When a single paper ID is requested (either directly or from Step 2):

```bash
python3 "$ARXIV_FETCHER" search "id:ARXIV_ID" --max 1
# or fallback:
python3 -c "
import urllib.request, xml.etree.ElementTree as ET
NS = 'http://www.w3.org/2005/Atom'
url = 'http://export.arxiv.org/api/query?id_list=ARXIV_ID'
with urllib.request.urlopen(url, timeout=30) as r:
    root = ET.fromstring(r.read())
# print full details ...
"
```

Display: title, all authors, categories, full abstract, published date, PDF URL, abstract URL, source URL.

### Step 4: Download Paper Artifacts

When download is requested, for each paper ID to download:

```bash
# Using fetch script:
python3 "$ARXIV_FETCHER" download ARXIV_ID --dir PAPER_DIR

This downloads both artifacts by default:
- `PAPER_DIR/ARXIV_ID.pdf`
- `PAPER_DIR/ARXIV_ID.src.tar.gz` when available
- extracted directory `PAPER_DIR/ARXIV_ID.src/` when extraction succeeds

Optional artifact override if needed:

```bash
python3 "$SCRIPT" download ARXIV_ID --dir PAPER_DIR --artifact pdf
python3 "$SCRIPT" download ARXIV_ID --dir PAPER_DIR --artifact source
```

After each download:
- Confirm PDF file size > 10 KB when PDF is downloaded
- Confirm source archive is non-trivial in size before extraction
- Add a 1-second delay between consecutive downloads to avoid rate limiting
- Report partial success cleanly when source is unavailable but PDF succeeds
- Preserve the source archive even if extraction fails

### Step 5: Summarize

For each paper (downloaded or fetched by API):

```markdown
## [Title]

- **arXiv**: [ID] - [abs_url]
- **Authors**: [full author list]
- **Date**: [published]
- **Categories**: [cs.LG, cs.AI, ...]
- **Abstract**: [full abstract]
- **Key contributions** (extracted from abstract):
  - [contribution 1]
  - [contribution 2]
  - [contribution 3]
- **Local PDF**: papers/[ID].pdf (if downloaded)
- **Local source archive**: papers/[ID].src.tar.gz (if available)
- **Extracted source directory**: papers/[ID].src/ (if extraction succeeded)
```

### Step 6: Update Research Wiki (if active)

**Required when `research-wiki/` exists in the project**; skip silently
otherwise. When the wiki dir exists, resolve `$WIKI_SCRIPT` per the
canonical chain at
[`shared-references/wiki-helper-resolution.md`](../shared-references/wiki-helper-resolution.md)
(Variant B — warn-and-skip), then ingest every paper returned by this
invocation:

```bash
if [ -d research-wiki/ ]; then
  cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
  ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null)}"
  WIKI_SCRIPT=".aris/tools/research_wiki.py"
  [ -f "$WIKI_SCRIPT" ] || WIKI_SCRIPT="tools/research_wiki.py"
  [ -f "$WIKI_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && WIKI_SCRIPT="$ARIS_REPO/tools/research_wiki.py"; }
  [ -f "$WIKI_SCRIPT" ] || {
    echo "WARN: research_wiki.py not found; arxiv results delivered, wiki ingest skipped. Fix: bash tools/install_aris.sh, export ARIS_REPO, or cp <ARIS-repo>/tools/research_wiki.py tools/." >&2
    WIKI_SCRIPT=""
  }
  if [ -n "$WIKI_SCRIPT" ]; then
    for each arxiv_id in results:
        python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
            --arxiv-id "<arxiv_id>"
  fi
fi
```

The helper handles metadata fetch, slug, dedup, page creation, index
rebuild, and log append in a single call — **do not handwrite
`papers/<slug>.md`**. See
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md)
for the canonical-helper rule. Missed ingests can be backfilled later
with `python3 "$WIKI_SCRIPT" sync research-wiki/ --arxiv-ids <id1>,<id2>,...`
after resolving `$WIKI_SCRIPT` as above.

### Step 7: Final Output

Summarize what was done:

- `Found N papers for "query"`
- `Downloaded PDF: papers/2301.07041.pdf (842 KB)`
- `Downloaded source: papers/2301.07041.src.tar.gz`
- `Extracted source: papers/2301.07041.src/`
- `Wiki-ingested N papers` (if `research-wiki/` was present)
- Any warnings (rate limit hit, file too small, source unavailable, extraction failed, already exists)

Suggest follow-up skills:

```text
/research-lit "topic"     - multi-source review with source-first local reading
/novelty-check "idea"     - verify your idea is novel against these papers
```

## Key Rules

- Always show the arXiv ID prominently - users need it for citations and reproducibility
- Verify downloaded PDFs: file must be > 10 KB; warn and discard if smaller
- Rate limit: wait 1 second between consecutive downloads; retry once after 5 seconds on HTTP 429
- Never overwrite an existing artifact at the same path - skip it and report `already exists`
- Handle both arXiv ID formats: new (`2301.07041`) and old (`cs/0601001`)
- PAPER_DIR is created automatically if it does not exist
- If source is unavailable or extraction fails, fall back cleanly to the PDF path
- If the arXiv API is unreachable, report the error clearly and suggest using `/research-lit` with `- sources: web` as a fallback
