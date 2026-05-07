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
- **FETCH_SCRIPT** - `tools/arxiv_fetch.py` relative to the ARIS install, or the same path relative to the current project. Fall back to inline Python if not found.

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

Locate the fetch script:

```bash
SCRIPT=$(python3 -c "
import pathlib
candidates = [
    pathlib.Path('tools/arxiv_fetch.py'),
    pathlib.Path.home() / '.claude' / 'skills' / 'arxiv' / 'arxiv_fetch.py',
]
for p in candidates:
    if p.exists():
        print(p)
        break
" 2>/dev/null)
```

**If SCRIPT is found**, run:

```bash
python3 "$SCRIPT" search "QUERY" --max MAX_RESULTS
```

**If SCRIPT is not found**, fall back to inline Python and return metadata only.

Present results as a table:

```text
| # | arXiv ID   | Title               | Authors        | Date       | Category |
|---|------------|---------------------|----------------|------------|----------|
| 1 | 2301.07041 | Attention Is All... | Vaswani et al. | 2017-06-12 | cs.LG    |
```

### Step 3: Fetch Details for a Specific ID

When a single paper ID is requested (either directly or from Step 2):

```bash
python3 "$SCRIPT" search "id:ARXIV_ID" --max 1
```

Display: title, all authors, categories, full abstract, published date, PDF URL, abstract URL, source URL.

### Step 4: Download Paper Artifacts

When download is requested, for each paper ID to download:

```bash
# Using fetch script:
python3 "$SCRIPT" download ARXIV_ID --dir PAPER_DIR
```

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
