---
name: research-lit
description: Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.
argument-hint: [paper-topic-or-url]
allowed-tools: Bash(*), Read, Glob, Grep, WebSearch, WebFetch, Write, Agent, mcp__zotero__*, mcp__obsidian-vault__*
---

# Research Literature Review

Research topic: $ARGUMENTS

## Constants


- **REVIEWER_BACKEND = `codex`** — Default: `codex exec` (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **PAPER_LIBRARY** — Local directory containing the user's paper collection and extracted source trees. Check these paths in order:
  1. `papers/` in the current project directory
  2. `literature/` in the current project directory
  3. Custom path specified by user in `CLAUDE.md` under `## Paper Library`
- **PREPARED_REPORT_DIR = `deep-research/`** — Preferred directory for prewritten deep research markdown reports generated outside this workflow.
- **MAX_PREPARED_REPORTS = 2** — In `— report: auto` mode, read at most the top 1-2 most relevant reports to avoid context bloat.
- **MAX_LOCAL_PAPERS = 20** — Maximum number of local paper bundles to scan. Prefer extracted `.tex` source when available; fall back to PDFs.
- **ARXIV_DOWNLOAD = true** — By default, download 10~20 most relevant arXiv reading artifacts to PAPER_LIBRARY after search: PDF plus source archive and extracted source tree when available.
- **ARXIV_MAX_DOWNLOAD = 20** — Maximum number of arXiv papers to download when `ARXIV_DOWNLOAD = true`.

## Non-Negotiable Execution Gate

When `ARXIV_DOWNLOAD = true` and arXiv search returns relevant paper IDs, this skill is **not allowed** to finish in a search-only / metadata-only state.

You must complete this full sequence before presenting the literature synthesis:
1. run one or more `python3 "$SCRIPT" download ... --dir papers/` commands for the top-ranked arXiv papers,
2. re-scan the augmented local paper library,
3. digest the newly available bundles through the source-first sub-agent path,
4. refresh `papers/index.md`,
5. verify that `papers/` artifacts and `papers/index.md` now exist for the current run.

If you only ran arXiv search / WebSearch and never executed the download commands, the run is incomplete. Go back and execute the download + local-ingestion stages before summarizing. The only valid exception is that no relevant arXiv papers were found or every download attempt failed despite being executed and reported.

> 💡 Overrides:
> - `/research-lit "topic" — paper library: ~/my_papers/` — custom local paper path
> - `/research-lit "topic" — sources: zotero, local` — only search Zotero + local paper bundles
> - `/research-lit "topic" — sources: zotero` — only search Zotero
> - `/research-lit "topic" — sources: web` — only search the web (skip all local)
> - `/research-lit "topic" — sources: web, semantic-scholar` — also search Semantic Scholar for published venue papers (IEEE, ACM, etc.)
> - `/research-lit "topic" — sources: deepxiv` — only search via DeepXiv progressive retrieval
> - `/research-lit "topic" — sources: all, deepxiv` — use default sources plus DeepXiv
> - `/research-lit "topic" — report: auto` — auto-detect the most relevant prepared markdown reports under `deep-research/` (default)
> - `/research-lit "topic" — report: none` — skip prepared markdown reports entirely
> - `/research-lit "topic" — report: deep-research/deep-research-report.md` — pin one prepared report explicitly
> - `/research-lit "topic" — arxiv download: false` — disable artifact download and use metadata only
> - `/research-lit "topic" — arxiv download: true, max download: 10` — download up to 10 arXiv paper bundles

## Data Sources

This skill checks multiple sources **in priority order**. All are optional — if a source is not configured or not requested, skip it silently.

### Source Selection

Parse `$ARGUMENTS` for a `— sources:` directive:
- **If `— sources:` is specified**: Only search the listed sources (comma-separated). Valid values: `zotero`, `obsidian`, `local`, `web`, `semantic-scholar`, `deepxiv`, `exa`, `gemini`, `openalex`, `all`.
- **If not specified**: Default to `all` — search every available source in priority order (`semantic-scholar`, `deepxiv`, `exa`, `gemini`, and `openalex` are **excluded** from `all`; they must be explicitly listed).

Examples:
```
/research-lit "diffusion models"                                    → all (default, source-first local reading)
/research-lit "diffusion models" — sources: all                     → all (default, source-first local reading)
/research-lit "diffusion models" — sources: zotero                  → Zotero only
/research-lit "diffusion models" — sources: zotero, web             → Zotero + web
/research-lit "diffusion models" — sources: local                   → local paper bundles only
/research-lit "topic" — sources: obsidian, local, web               → skip Zotero
/research-lit "topic" — sources: web, semantic-scholar              → web + S2 API (IEEE/ACM venue papers)
/research-lit "topic" — sources: deepxiv                            → DeepXiv only
/research-lit "topic" — sources: all, deepxiv                       → default sources + DeepXiv
/research-lit "topic" — sources: all, semantic-scholar              → all + S2 API
/research-lit "topic" — sources: exa                               → Exa only (broad web + content extraction)
/research-lit "topic" — sources: all, exa                          → default sources + Exa web search
/research-lit "topic" — sources: gemini                            → Gemini only (AI-powered broad discovery)
/research-lit "topic" — sources: all, gemini                       → default sources + Gemini discovery
/research-lit "topic" — sources: gemini, semantic-scholar           → Gemini + S2 (broad discovery + venue metadata)
/research-lit "topic" — sources: openalex                          → OpenAlex only (open citation graph + institutions)
/research-lit "topic" — sources: semantic-scholar, openalex         → S2 + OpenAlex (complementary metadata)
```

### Source Table

| Priority | Source | ID | How to detect | What it provides |
|----------|--------|----|---------------|-----------------|
| 1 | **Zotero** (via MCP) | `zotero` | Try calling any `mcp__zotero__*` tool — if unavailable, skip | Collections, tags, annotations, PDF highlights, BibTeX, semantic search |
| 2 | **Obsidian** (via MCP) | `obsidian` | Try calling any `mcp__obsidian-vault__*` tool — if unavailable, skip | Research notes, paper summaries, tagged references, wikilinks |
| 3 | **Prepared markdown reports** | `report` | `Glob: deep-research/*.md` or explicit `— report: <path>` | Precomputed deep research synthesis: framing, theme clusters, gap statements, benchmarks, open questions |
| 4 | **Local paper bundles** | `local` | `Glob: papers/**/*.pdf, papers/**/*.src.tar.gz, papers/**/*.tex, literature/**/*.pdf, literature/**/*.src.tar.gz, literature/**/*.tex` | Extracted LaTeX source when available, otherwise source archive / PDF fallback |
| 5 | **Web search** | `web` | Always available (WebSearch) | arXiv, Semantic Scholar, Google Scholar |
| 6 | **Semantic Scholar API** | `semantic-scholar` | `$S2_FETCHER` resolves (canonical name `semantic_scholar_fetch.py`, per integration-contract §2) | Published venue papers (IEEE, ACM, Springer) with structured metadata: citation counts, venue info, TLDR. **Only runs when explicitly requested** via `— sources: semantic-scholar` or `— sources: web, semantic-scholar` |
| 7 | **DeepXiv CLI** | `deepxiv` | `$DEEPXIV_FETCHER` resolves (canonical name `deepxiv_fetch.py`, per integration-contract §2) **and** `deepxiv` CLI present (`command -v deepxiv`) | Progressive paper retrieval: search, brief, head, section, trending, web search. **Only runs when explicitly requested** via `— sources: deepxiv` or `— sources: all, deepxiv` |
| 8 | **Exa Search** | `exa` | `$EXA_FETCHER` resolves (canonical name `exa_search.py`, per integration-contract §2); fetcher handles `exa-py` SDK + API key internally | AI-powered broad web search with content extraction (highlights, text, summaries). Covers blogs, docs, news, companies, and research papers beyond arXiv/S2. **Only runs when explicitly requested** via `— sources: exa` or `— sources: all, exa` |
| 9 | **Gemini** (MCP / CLI) | `gemini` | `mcp__gemini-cli__ask-gemini` tool available, or `gemini` CLI installed | AI-powered broad literature discovery — decomposes topics into sub-problems, aliases, and variants for wider retrieval. Prefers MCP, falls back to CLI. **Only runs when explicitly requested** via `— sources: gemini` or `— sources: all, gemini` |
| 10 | **OpenAlex** | `openalex` | `$OPENALEX_FETCHER` resolves (canonical name `openalex_fetch.py`, per integration-contract §2) **and** Python `requests` module importable | Open citation graph with institutional affiliations, funding data, and comprehensive metadata across 250M+ works. Fully open API. **Only runs when explicitly requested** via `— sources: openalex` or `— sources: all, openalex` |

> **Graceful degradation**: If no MCP servers are configured, the skill works exactly as before (local paper bundles + web search). Zotero and Obsidian are pure additions.

## Workflow

### Step 0a: Search Zotero Library (if available)

**Skip this step entirely if Zotero MCP is not configured.**

Try calling a Zotero MCP tool (e.g., search). If it succeeds:

1. **Search by topic**: Use the Zotero search tool to find papers matching the research topic
2. **Read collections**: Check if the user has a relevant collection/folder for this topic
3. **Extract annotations**: For highly relevant papers, pull PDF highlights and notes — these represent what the user found important
4. **Export BibTeX**: Get citation data for relevant papers (useful for `/paper-write` later)
5. **Compile results**: For each relevant Zotero entry, extract:
   - Title, authors, year, venue
   - User's annotations/highlights (if any)
   - Tags the user assigned
   - Which collection it belongs to

> 📚 Zotero annotations are gold — they show what the user personally highlighted as important, which is far more valuable than generic summaries.

### Step 0b: Search Obsidian Vault (if available)

**Skip this step entirely if Obsidian MCP is not configured.**

Try calling an Obsidian MCP tool (e.g., search). If it succeeds:

1. **Search vault**: Search for notes related to the research topic
2. **Check tags**: Look for notes tagged with relevant topics (e.g., `#diffusion-models`, `#paper-review`)
3. **Read research notes**: For relevant notes, extract the user's own summaries and insights
4. **Follow links**: If notes link to other relevant notes (wikilinks), follow them for additional context
5. **Compile results**: For each relevant note:
   - Note title and path
   - User's summary/insights
   - Links to other notes (research graph)
   - Any frontmatter metadata (paper URL, status, rating)

> 📝 Obsidian notes represent the user's **processed understanding** — more valuable than raw paper content for understanding their perspective.

### Step 0c: Read Prepared Deep Research Reports (if available)

Before searching online, check whether the user already has synthesized markdown reports in `PREPARED_REPORT_DIR`.

Parse `$ARGUMENTS` for a `— report:` directive:
- `— report: auto` (default) → auto-detect the most relevant reports in `deep-research/*.md`
- `— report: none` → skip this step entirely
- `— report: <path>` → read that specific markdown report first

In `— report: auto` mode, prefer reports in this order:
1. `deep-research/deep-research-report.md`
2. filenames matching the topic
3. filenames containing `Literature Review`, `Survey`, `Review`, or `Gap`
4. other recent markdown reports

Read at most `MAX_PREPARED_REPORTS` reports. Treat them as **precomputed local synthesis**, not as final truth.

From each selected report, extract only the reusable structure:
- problem framing and terminology
- theme clusters / approach buckets
- named methods and papers
- explicit gap statements
- benchmarks, datasets, and evaluation dimensions
- unresolved contradictions or open questions

Summarize this into a compact "prepared report synthesis" section that feeds the rest of the workflow.

> 🧭 Use prepared reports to start from the strongest existing synthesis, but still verify freshness with current search before making novelty or scope claims.

### Step 0d: Scan Local Paper Library

Before searching online, check if the user already has relevant papers locally.

1. **Locate library**: Check PAPER_LIBRARY paths for paper bundles
   ```
   Glob: papers/**/*.pdf, papers/**/*.src.tar.gz, papers/**/*.tex, literature/**/*.pdf, literature/**/*.src.tar.gz, literature/**/*.tex
   ```

2. **Resolve one bundle per paper**:
   - Prefer extracted `.tex` source trees when available
   - Otherwise use source archives if present but not yet extracted
   - Otherwise use PDFs
   - Avoid treating `paper.pdf` and `paper.src/main.tex` as separate papers

3. **De-duplicate against Zotero and prepared reports**: If Step 0a or Step 0c already surfaced a paper, skip duplicated local bundles when possible (match by filename or title).

4. **Filter by relevance**: Match filenames and available title/abstract text against the research topic. Skip clearly unrelated papers.

5. **Digest relevant local bundles via a sub-agent contract**: For each relevant local bundle (up to MAX_LOCAL_PAPERS), do **not** read raw `.tex` directly into the main context by default. Instead, delegate bounded source digestion to a sub-agent and only keep the returned structured digest. Each sub-agent must also resolve the paper's reading artifacts for later indexing: record the project-relative `pdf_path` when a PDF exists, record `source_coverage.main_tex_path` when a readable main TeX file exists, and return a one-paragraph `brief_summary` plus normalized `problem`, `method`, `result`, and `takeaway` fields for `papers/index.md`.

   ### Mode A — `broad_sweep`
   Use this as the default local-bundle read mode.

   Purpose:
   - recover title / abstract / introduction-level understanding
   - classify the paper as `direct | adjacent | tangential | unclear`
   - decide whether the paper deserves deeper inspection

   Read rules for the sub-agent:
   - identify the likely main `.tex` using this heuristic order:
     1. file containing `\documentclass` and `\begin{document}`
     2. file containing `\title{` or `\begin{abstract}`
     3. `main.tex`
     4. largest top-level `.tex`
   - inspect `\input{}` / `\include{}` only as needed to recover title / abstract / introduction
   - do **not** read method, experiments, appendix, or the whole source tree by default
   - if no readable source exists, fall back to the first 3 pages of the PDF
   - return **only** the schema below; no long quotes, no raw LaTeX, no general commentary

   Required output schema:
   ```yaml
   mode: broad_sweep
   paper_id: "..."
   bundle_path: "..."
   pdf_path: "papers/...pdf | literature/...pdf | null"
   artifact_used: "tex_source | pdf | metadata_only"
   confidence: "high | medium | low"
   bibliography:
     title: "..."
     authors: ["..."]
     year: "..."
     venue: "..."
   source_coverage:
     main_tex_found: true
     main_tex_path: "..."
     sections_inspected: ["title", "abstract", "introduction"]
     extra_files_opened: ["..."]
   digest:
     brief_summary: "..."
     problem: "..."
     method: "..."
     results: "..."
     takeaway: "..."
     relevance: "..."
     relation_label: "direct | adjacent | tangential | unclear"
   signals:
     why_relevant: ["..."]
     notable_entities:
       datasets: ["..."]
       baselines: ["..."]
       tasks: ["..."]
   recommended_next_action:
     action: "stop | deep_read"
     reason: "..."
   evidence_notes: ["..."]
   failure_mode: "none | missing_main_tex | unreadable_source | insufficient_intro | pdf_fallback_used"
   ```

   ### Mode B — `deep_read`
   Escalate only for closest prior work or when stronger method/results detail is needed.

   Escalation triggers:
   - `relation_label == direct`
   - or `recommended_next_action.action == deep_read`
   - or Step 2 still needs concrete method/results detail for novelty differentiation

   Read rules for the sub-agent:
   - read abstract, introduction, method, and experiments only
   - follow `\input{}` / `\include{}` selectively for those sections
   - do **not** read the full source tree
   - do **not** read appendix unless critical evaluation evidence is missing from the main sections
   - if source is unreadable or incomplete, fall back to PDF selectively
   - return concise paraphrases only; no raw LaTeX and no adversarial review framing

   Required output schema:
   ```yaml
   mode: deep_read
   paper_id: "..."
   bundle_path: "..."
   pdf_path: "papers/...pdf | literature/...pdf | null"
   artifact_used: "tex_source | pdf | metadata_only"
   confidence: "high | medium | low"
   bibliography:
     title: "..."
     authors: ["..."]
     year: "..."
     venue: "..."
   source_coverage:
     main_tex_found: true
     main_tex_path: "..."
     sections_requested: ["abstract", "introduction", "method", "experiments"]
     sections_inspected: ["..."]
     extra_files_opened: ["..."]
     appendix_inspected: false
   normalized_digest:
     brief_summary: "..."
     problem: "..."
     method: "..."
     results: "..."
     takeaway: "..."
     relevance: "..."
     source: "local"
     artifact: "tex_source | pdf | metadata_only"
   closest_prior_work_assessment:
     central_claim: "..."
     technical_core: ["..."]
     experiment_scope:
       tasks: ["..."]
       datasets: ["..."]
       metrics: ["..."]
       baselines: ["..."]
     strongest_result:
       claim: "..."
       evidence: "..."
     limitations_or_boundaries: ["..."]
   differentiation_hooks:
     likely_overlap_axes: ["..."]
     likely_non_overlap_axes: ["..."]
     followup_questions: ["..."]
   evidence_notes:
     abstract_intro_basis: ["..."]
     method_basis: ["..."]
     experiment_basis: ["..."]
   read_completeness:
     sufficient_for_related_work: true
     sufficient_for_novelty_differentiation: true
     missing_for_full_understanding: ["..."]
   failure_mode: "none | missing_method_section | missing_experiments_section | unreadable_source | pdf_fallback_used"
   ```

6. **Build local knowledge base**: Compile the returned digests into a "papers you already have" section. Use `broad_sweep` as the default and only promote a small number of direct papers to `deep_read`.

7. **Write `papers/index.md`**: After local bundle digestion (and again after any new arXiv bundles are downloaded and digested), generate or refresh `papers/index.md` as a reusable paper-library index.
   - Treat this as a required output of a successful source-ingestion pass whenever any relevant local or newly downloaded bundles were digested. Do not consider the literature-ingestion stage complete until the index has been refreshed.
   - Write one entry per resolved paper bundle, not one per artifact file.
   - Reuse the sub-agent outputs instead of rereading raw `.tex` in the main workflow.
   - Prefer project-relative paths.
   - If `papers/index.md` already exists, update matching `paper_id` entries in place and append new papers; do not drop unrelated prior entries.
   - Required fields per paper:
     - `paper_id`
     - `title`
     - `pdf_path`
     - `main_tex_path`
     - `artifact_used`
     - `brief_summary`
     - `problem`
     - `method`
     - `result`
     - `takeaway`
     - `relation_label`
     - `confidence`
   - If `deep_read` exists for a paper, let its normalized digest overwrite the corresponding `broad_sweep` summary fields in the index.
   - Recommended format:

   ```markdown
   # Paper Index

   | Paper | PDF | Main TeX | Artifact | Summary | Problem | Method | Result | Takeaway |
   |-------|-----|----------|----------|---------|---------|--------|--------|----------|
   | ... | `papers/foo.pdf` | `papers/foo.src/main.tex` | tex_source | ... | ... | ... | ... | ... |
   ```

> 📚 Prefer source-first reading because PDF text extraction often pollutes context with broken lines, headers, and damaged math. Keep raw `.tex` out of the main context whenever possible; retain only the digest returned by the sub-agent.

### Step 1: Search (external)
- Use WebSearch to find recent papers on the topic
- Check arXiv, Semantic Scholar, Google Scholar
- Focus on papers from last 2 years unless studying foundational work
- **De-duplicate**: Skip papers already found in Zotero, Obsidian, prepared reports, or local library
- **Verify freshness**: treat prepared reports as a strong starting point, then explicitly confirm whether newer competing work, changed terminology, or better benchmark evidence has appeared since those reports were written

**arXiv API search** (always runs):
**arXiv API search** (runs when `— sources:` is unset, contains `web` or `all`; no download by default — arXiv API is part of the Priority-4 Web tier, see Source Table above):

**Policy D2 tracking discipline (orchestrator-managed)**: the
executor (you, the LLM) maintains an in-context list of contributing
sources. For **helper-backed bash sources** (arxiv, semantic-scholar,
deepxiv, exa, openalex), a source contributes iff its bash block
ran its helper successfully (helper resolved AND invocation exited 0;
note: the helper exiting 0 with an empty result list still counts as
"ran" — downstream relevance ranking is what decides whether the user
actually sees content). For **non-helper sources** (zotero / obsidian /
local PDF / WebSearch / Gemini), the contribution rule is stated in
the Step-1 finalization block below — these are tracked separately
because they don't emit `D2 contribution:` log lines from bash. Sources
that were not requested via `— sources:` do not count. At the end of
Step 1 (before "Optional PDF download"), if zero sources contributed,
surface a D2 empty-aggregate error and stop. (See
integration-contract.md §2 Policy D2 — the in-context tracking
replaces a shared bash accumulator because SKILL bash blocks are
executed as separate shells; state does not survive.)

Resolve `$ARXIV_FETCHER` via the canonical chain (Policy D2 — this
source contributes to the multi-source aggregate; warn-and-continue
on failure, never abort the whole aggregate):

```bash
# Canonical strict-safe resolver (see shared-references/integration-contract.md §2).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
ARXIV_FETCHER=".aris/tools/arxiv_fetch.py"
[ -f "$ARXIV_FETCHER" ] || ARXIV_FETCHER="tools/arxiv_fetch.py"
[ -f "$ARXIV_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && ARXIV_FETCHER="$ARIS_REPO/tools/arxiv_fetch.py"; }
[ -f "$ARXIV_FETCHER" ] || ARXIV_FETCHER=""

if [ -n "$ARXIV_FETCHER" ]; then
  # Search arXiv API for structured results (title, abstract, authors, categories).
  # Wrap with if/then/else so set -e doesn't abort the SKILL.
  if python3 "$ARXIV_FETCHER" search "QUERY" --max 10; then
    echo "D2 contribution: arxiv (helper invocation exit 0)" >&2
  else
    echo "WARN: arxiv_fetch.py invocation failed; D2 aggregate continues with WebSearch results." >&2
  fi
else
  echo "WARN: arxiv_fetch.py not resolved; falling back to WebSearch for arXiv hits." >&2
fi
```

> **Record-keeping**: track the `D2 contribution: …` lines emitted by
> each source's bash block. They form the contributing-source list
> the orchestrator uses for the Step-1 finalization gate below.
> WebSearch (Priority 4) is treated as having contributed iff
> WebSearch was requested (no `— sources:` filter, or the list
> contains `web` or `all`) AND was actually invoked; the orchestrator
> records that separately. (The finalization block below restates
> this rule canonically — both lines must stay in sync.)

If `$ARXIV_FETCHER` is empty (D2 graceful degradation), fall back to WebSearch for arXiv (same as before).

The arXiv API returns structured metadata (title, abstract, full author list, categories, dates) — richer than WebSearch snippets. Merge these results with the other sources and de-duplicate.

**Semantic Scholar API search** (only when `semantic-scholar` is in sources):

When the user explicitly requests `— sources: semantic-scholar` (or `— sources: web, semantic-scholar`), search for published venue papers beyond arXiv.


```bash
# Re-resolve $ARIS_REPO (SKILL bash blocks may run in separate shells).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
# Resolve $S2_FETCHER (Policy D2 — warn-and-skip on missing).
S2_FETCHER=".aris/tools/semantic_scholar_fetch.py"
[ -f "$S2_FETCHER" ] || S2_FETCHER="tools/semantic_scholar_fetch.py"
[ -f "$S2_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && S2_FETCHER="$ARIS_REPO/tools/semantic_scholar_fetch.py"; }
[ -f "$S2_FETCHER" ] || S2_FETCHER=""

if [ -n "$S2_FETCHER" ]; then
  # Search for published CS/Engineering papers with quality filters.
  # Wrap with if/then/else so set -e doesn't abort the SKILL.
  if python3 "$S2_FETCHER" search "QUERY" --max 10 \
      --fields-of-study "Computer Science,Engineering" \
      --publication-types "JournalArticle,Conference"; then
    echo "D2 contribution: semantic_scholar (helper invocation exit 0)" >&2
  else
    echo "WARN: semantic_scholar_fetch.py invocation failed; D2 aggregate continues with remaining sources." >&2
  fi
fi
```

If `$S2_FETCHER` is empty (canonical chain exhausted), skip silently — D2 multi-source aggregate continues with the remaining resolved sources.

**Why use Semantic Scholar?** Many IEEE/ACM journal papers are NOT on arXiv. S2 fills the gap for published venue-only papers with citation counts and venue metadata.

**De-duplication between arXiv and S2**: Match by arXiv ID (S2 returns `externalIds.ArXiv`):
- If a paper appears in both: check S2's `venue`/`publicationVenue` — if it has been published in a journal/conference (e.g. IEEE TWC, JSAC), use S2's metadata (venue, citationCount, DOI) as the authoritative version, since the published version supersedes the preprint. Keep the arXiv PDF link for download.
- If the S2 match has no venue (still just a preprint indexed by S2): keep the arXiv version as-is.
- S2 results without `externalIds.ArXiv` are **venue-only papers** not on arXiv — these are the unique value of this source.

**DeepXiv search** (only when `deepxiv` is in sources):

When the user explicitly requests `— sources: deepxiv` (or includes `deepxiv` in a combined source list), use the DeepXiv adapter for progressive retrieval:

```bash
# Re-resolve $ARIS_REPO (SKILL bash blocks may run in separate shells).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
# Resolve $DEEPXIV_FETCHER (Policy D2 — warn-and-skip on missing).
DEEPXIV_FETCHER=".aris/tools/deepxiv_fetch.py"
[ -f "$DEEPXIV_FETCHER" ] || DEEPXIV_FETCHER="tools/deepxiv_fetch.py"
[ -f "$DEEPXIV_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && DEEPXIV_FETCHER="$ARIS_REPO/tools/deepxiv_fetch.py"; }
[ -f "$DEEPXIV_FETCHER" ] || DEEPXIV_FETCHER=""

if [ -n "$DEEPXIV_FETCHER" ] && command -v deepxiv >/dev/null 2>&1; then
  # Wrap each adapter call so set -e doesn't abort the SKILL.
  if python3 "$DEEPXIV_FETCHER" search "QUERY" --max 10; then
    echo "D2 contribution: deepxiv (helper invocation exit 0)" >&2

    # Then deepen only for the most relevant papers (sub-calls don't change D2 aggregate count):
    python3 "$DEEPXIV_FETCHER" paper-brief ARXIV_ID \
      || echo "WARN: deepxiv_fetch.py paper-brief failed; skipping deepen step." >&2
    python3 "$DEEPXIV_FETCHER" paper-head ARXIV_ID \
      || echo "WARN: deepxiv_fetch.py paper-head failed; skipping deepen step." >&2
    python3 "$DEEPXIV_FETCHER" paper-section ARXIV_ID "Experiments" \
      || echo "WARN: deepxiv_fetch.py paper-section failed; skipping deepen step." >&2
  else
    echo "WARN: deepxiv_fetch.py search invocation failed; D2 aggregate continues with remaining sources." >&2
  fi
fi
```

If `$DEEPXIV_FETCHER` is empty or the `deepxiv` CLI is unavailable, skip this source gracefully and continue with the remaining requested sources (Policy D2 graceful degradation).

**Why use DeepXiv?** It is useful when a broad search should be followed by staged reading rather than immediate full-paper loading. This reduces unnecessary context while still surfacing structure, TLDRs, and the most relevant sections.

**De-duplication against arXiv and S2**:
- Match by arXiv ID first, DOI second, normalized title third
- If DeepXiv and arXiv refer to the same preprint, keep one canonical paper row and record `deepxiv` as an additional source
- If DeepXiv overlaps with S2 on a published paper, prefer S2 venue/citation metadata in the final table, but keep DeepXiv-derived section notes when they add value

**Exa search** (only when `exa` is in sources):

When the user explicitly requests `— sources: exa` (or includes `exa` in a combined source list), use the Exa tool for broad AI-powered web search with content extraction:

```bash
# Re-resolve $ARIS_REPO (SKILL bash blocks may run in separate shells).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
# Resolve $EXA_FETCHER (Policy D2 — warn-and-skip on missing).
EXA_FETCHER=".aris/tools/exa_search.py"
[ -f "$EXA_FETCHER" ] || EXA_FETCHER="tools/exa_search.py"
[ -f "$EXA_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && EXA_FETCHER="$ARIS_REPO/tools/exa_search.py"; }
[ -f "$EXA_FETCHER" ] || EXA_FETCHER=""

if [ -n "$EXA_FETCHER" ]; then
  # Search for research papers with highlights.
  # Wrap with if/then/else so set -e doesn't abort the SKILL.
  exa_contributed=false
  if python3 "$EXA_FETCHER" search "QUERY" --max 10 --category "research paper" --content highlights; then
    exa_contributed=true
  else
    echo "WARN: exa_search.py research-paper invocation failed; D2 aggregate continues." >&2
  fi
  # Search for broader web content (blogs, docs, news)
  if python3 "$EXA_FETCHER" search "QUERY" --max 10 --content highlights; then
    exa_contributed=true
  else
    echo "WARN: exa_search.py broad-web invocation failed; D2 aggregate continues." >&2
  fi
  [ "$exa_contributed" = "true" ] && echo "D2 contribution: exa (at least one invocation exit 0)" >&2
fi
```

If `$EXA_FETCHER` is empty or the `exa-py` SDK is unavailable, skip this source gracefully and continue with the remaining requested sources (Policy D2 graceful degradation).

**Why use Exa?** Exa provides AI-powered search across the broader web (blogs, documentation, news, company pages) with built-in content extraction. It fills a gap between academic databases (arXiv, S2) and generic WebSearch by returning richer content with each result.

**De-duplication against arXiv, S2, and DeepXiv**:
- Match by URL first, then normalized title
- If Exa returns an arXiv paper already found by arXiv/S2, prefer the structured metadata from those sources
- Exa results from non-academic domains (blogs, docs, news) are unique value not covered by other sources

**Gemini search** (only when `gemini` is in sources):

When the user explicitly requests `— sources: gemini` (or includes `gemini` in a combined source list), use Gemini for AI-powered broad literature discovery.

**Priority 1 — Gemini MCP** (preferred): Call `mcp__gemini-cli__ask-gemini` with the search prompt:

```
mcp__gemini-cli__ask-gemini({
  prompt: 'You are a research literature scout. Search comprehensively for papers on: "QUERY"

IMPORTANT CONSTRAINTS:
1. Search from MULTIPLE angles — decompose the topic into sub-problems, aliases, neighboring tasks, and common benchmark/settings variants.
2. Prefer papers that are genuinely relevant, not merely keyword-adjacent.
3. Include top venues, journals, surveys, recent preprints, and papers with code when available.
4. Focus on papers from 2022 onward unless older foundational work is necessary.

For EACH paper found, provide ALL of the following:
- Title: [exact title]
- Authors: [full author list]
- Year: [publication year]
- Venue: [exact conference/journal name + year, or "arXiv preprint"]
- arXiv ID: [format 2401.12345, or "N/A"]
- DOI: [if available, or "N/A"]
- Code URL: [GitHub/GitLab link if available, or "No code"]
- Summary: [one-sentence core contribution]

Find at least 15 papers.',
  model: 'gemini-2.5-pro'
})
```

**Priority 2 — Gemini CLI fallback** (if MCP unavailable): Use `gemini -p "...same prompt..." 2>/dev/null` via Bash (timeout: 120s).

If both MCP and CLI are unavailable, skip this source gracefully and continue with the remaining requested sources.

**Why use Gemini?** Gemini provides AI-driven discovery that goes beyond keyword matching — it decomposes topics, explores naming variants, and surfaces papers that traditional API-based searches (arXiv, S2) may miss. It fills a different retrieval niche from structured database queries.

**De-duplication against arXiv, S2, DeepXiv, and Exa**:
- Match by arXiv ID first, DOI second, normalized title third
- If Gemini returns a paper already found by S2, prefer S2's citation count and venue metadata
- If Gemini returns a paper already found by arXiv, prefer arXiv's structured metadata
- Gemini's unique value is discovering papers that other keyword-based indexes did not surface
- **Do not use Gemini-reported citation counts** — they may be inaccurate. Use S2 for authoritative citation data.

**OpenAlex search** (only when `openalex` is in sources):

When the user explicitly requests `— sources: openalex` (or includes `openalex` in a combined source list), use OpenAlex API for comprehensive academic metadata:

```bash
# Re-resolve $ARIS_REPO (SKILL bash blocks may run in separate shells).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
# Resolve $OPENALEX_FETCHER (Policy D2 — warn-and-skip on missing).
OPENALEX_FETCHER=".aris/tools/openalex_fetch.py"
[ -f "$OPENALEX_FETCHER" ] || OPENALEX_FETCHER="tools/openalex_fetch.py"
[ -f "$OPENALEX_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && OPENALEX_FETCHER="$ARIS_REPO/tools/openalex_fetch.py"; }
[ -f "$OPENALEX_FETCHER" ] || OPENALEX_FETCHER=""

# Preflight: skip OpenAlex silently if the helper is unresolved OR the
# `requests` Python package is missing. Both checks must pass before
# the script is invoked, so users without `requests` installed never see
# a stack trace from a default `/research-lit` run.
if [ -z "$OPENALEX_FETCHER" ] || ! python3 -c "import requests" >/dev/null 2>&1; then
  echo "OpenAlex source not available (openalex_fetch.py unresolved or 'requests' module missing); skipping." >&2
else
  # Search for papers with comprehensive metadata.
  # Wrap with if/then/else so set -e doesn't abort the SKILL.
  if python3 "$OPENALEX_FETCHER" search "QUERY" --max 10 \
      --year "2022-" \
      --type article \
      --sort relevance; then
    echo "D2 contribution: openalex (helper invocation exit 0)" >&2
  else
    echo "WARN: openalex_fetch.py invocation failed; D2 aggregate continues with remaining sources." >&2
  fi
fi
```

If `openalex_fetch.py` is not found or `requests` module is missing, skip this source gracefully and continue with the remaining requested sources.

**Why use OpenAlex?** Fully open citation graph (no API key required), institutional affiliations, funding data (NSF, NIH), comprehensive topic/keyword metadata, and coverage across all disciplines (not just CS).

**De-duplication against arXiv, S2, DeepXiv, Exa, and Gemini**:
- Match by DOI first (OpenAlex has DOI for most works), then arXiv ID, then normalized title
- If OpenAlex and S2 both have the same paper:
  - Prefer S2 for citation counts (more up-to-date)
  - Prefer S2 for venue metadata (more accurate for CS/AI papers)
  - Use OpenAlex for institutional affiliations and funding data (unique value)
  - Merge both into a richer record
- If OpenAlex and arXiv overlap, prefer arXiv's PDF link and metadata, but keep OpenAlex's citation/institution data
- OpenAlex's unique value: institutional affiliations, funding sources, comprehensive topic classification, and cross-discipline coverage

**Required arXiv artifact download stage** (default-on when `ARXIV_DOWNLOAD = true`):

After all sources are searched and papers are ranked by relevance, the expected execution order is:
1. download top-ranked arXiv bundles into `papers/`
2. re-scan the augmented local paper library
3. digest the newly available bundles through the same source-first sub-agent path
4. refresh `papers/index.md`
5. only then finalize the literature synthesis
**D2 aggregate finalization** (per integration-contract §2 Policy D2):

The orchestrator (you, the LLM) maintains an in-context list of
contributing sources by reading the `D2 contribution: <name>` log
lines emitted by each source's bash block above, plus:

- `zotero` if Step 0a returned non-empty Zotero hits.
- `obsidian` if Step 0b returned non-empty Obsidian hits.
- `local` if Step 0c found at least one relevant local PDF.
- `web` if WebSearch (Priority 4) was requested (either no `— sources:`
  filter, or the list contains `web` or `all`) AND was actually invoked.
  Note: `— sources: all` covers the default-on tier (zotero, obsidian,
  local, web) — it does **NOT** include the opt-in fetchers
  (semantic-scholar, deepxiv, exa, gemini, openalex). To enable those,
  add them explicitly (e.g. `— sources: all, semantic-scholar, openalex`),
  matching the existing convention at L42-43 / L51-63 of this SKILL.
- `gemini` if Gemini MCP / CLI returned at least one paper.

If the resulting contributing-source list has zero entries, surface:

> **ERROR**: D2 aggregate empty — every requested source either was
> unresolved, not invoked, failed, or (for MCP / local PDF / Gemini
> sources) returned no usable result. (Note: WebSearch contributes
> when requested and invoked, even if the result set is empty.) The
> multi-source aggregate cannot proceed. Suggest the user retry with
> a wider `— sources:` list (e.g. `web, local`) or check helper
> resolution and SDK installation.

Then stop before Step 1.5. Otherwise log the contributing-source
list to the user (e.g. "Sources contributed: arxiv, semantic_scholar,
web") and proceed.

**Optional PDF download** (only when `ARXIV_DOWNLOAD = true`):

```bash
# Re-resolve $ARXIV_FETCHER (SKILL bash blocks may run in separate shells).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
ARXIV_FETCHER=".aris/tools/arxiv_fetch.py"
[ -f "$ARXIV_FETCHER" ] || ARXIV_FETCHER="tools/arxiv_fetch.py"
[ -f "$ARXIV_FETCHER" ] || { [ -n "${ARIS_REPO:-}" ] && ARXIV_FETCHER="$ARIS_REPO/tools/arxiv_fetch.py"; }
[ -f "$ARXIV_FETCHER" ] || ARXIV_FETCHER=""

# Download top N most relevant arXiv papers; skip silently if helper unresolved.
[ -n "$ARXIV_FETCHER" ] && python3 "$ARXIV_FETCHER" download ARXIV_ID --dir papers/
```
- Download top `ARXIV_MAX_DOWNLOAD` arXiv papers by relevance
- Download PDF plus source archive / extracted tree when available
- Skip artifacts already in the local library
- 1-second delay between downloads (rate limiting)
- Preserve partial success when source is unavailable but PDF succeeds
- After download, treat the new bundles as part of the same local paper library flow: run the same sub-agent digestion, capture `pdf_path` / `main_tex_path`, and refresh `papers/index.md`
- Do not silently skip the re-scan / digestion / index-refresh portion when downloads succeed; later phases depend on those artifacts and index entries existing
- Before Step 3, explicitly verify the outcome with `Glob` over `papers/**/*.pdf`, `papers/**/*.src.tar.gz`, `papers/**/*.tex` (or `literature/**` if that is the configured library) plus `Read papers/index.md` when the index should exist
- If those verification checks fail after relevant arXiv hits were found and downloads were expected, treat the run as incomplete and continue the download / ingestion path instead of presenting a search-only synthesis
- This stage is part of the intended default literature-ingestion flow, not an optional nice-to-have when `ARXIV_DOWNLOAD = true`
- The purpose is to let `research-lit` own paper discovery plus first-pass reading from local artifacts before later proposal-specific novelty checks

### Step 1.5: Verify Candidate Papers (anti-hallucination, mandatory)

Before analysis, run pre-search verification on **all** candidate papers
collected from Steps 0a-1 to filter out LLM-fabricated arXiv IDs / DOIs /
titles. Helper: `verify_papers.py` (canonical name; resolved per
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2,
Policy D1 — primary helper with degraded-output fallback). If the
helper is unresolved on this machine, the SKILL emits a fallback
`verified_papers.json` tagging every candidate `[UNVERIFIED]` so
downstream analysis proceeds with audit-visible degraded output
rather than silently dropping candidates.

```bash
# 1. Resolve $VERIFY_PAPERS via the canonical strict-safe chain (§2).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
VERIFY_PAPERS=".aris/tools/verify_papers.py"
[ -f "$VERIFY_PAPERS" ] || VERIFY_PAPERS="tools/verify_papers.py"
[ -f "$VERIFY_PAPERS" ] || { [ -n "${ARIS_REPO:-}" ] && VERIFY_PAPERS="$ARIS_REPO/tools/verify_papers.py"; }
[ -f "$VERIFY_PAPERS" ] || VERIFY_PAPERS=""

# 2. Emit candidates as JSON. Verification scratch lives under .aris/
#    (NOT under research-wiki/ — Step 6's wiki ingest predicate is
#    "research-wiki/ exists", and we must not trip it from Step 1.5).
mkdir -p .aris/verify-papers
cat > .aris/verify-papers/candidate_papers.json <<'JSON'
[
  {"id": "p1", "arxiv_id": "2307.03172", "doi": null, "title": "Lost in the Middle"},
  {"id": "p2", "arxiv_id": null, "doi": "10.1145/...", "title": "..."},
  {"id": "p3", "arxiv_id": null, "doi": null, "title": "Some Paper Title"}
]
JSON

# 3. Run 3-layer verification (arXiv batch → CrossRef → Semantic Scholar fuzzy).
#    Policy D1: when the helper is unresolved OR its invocation fails, emit
#    a degraded verified set tagging everything [UNVERIFIED] so the user
#    can audit search quality. If python3 itself is missing, we BLOCK
#    rather than hand-roll JSON in shell.
verify_ok=false
if [ -n "$VERIFY_PAPERS" ]; then
  if python3 "$VERIFY_PAPERS" \
        --input  .aris/verify-papers/candidate_papers.json \
        --output .aris/verify-papers/verified_papers.json; then
    verify_ok=true
  else
    echo "WARN: verify_papers.py invocation failed (resolved at $VERIFY_PAPERS); falling back to [UNVERIFIED] tagging." >&2
  fi
else
  echo "WARN: verify_papers.py not resolved at .aris/tools/, tools/, or \$ARIS_REPO/tools/." >&2
  echo "      Fix: rerun bash tools/install_aris.sh, export ARIS_REPO, or copy the helper to tools/." >&2
fi
if [ "$verify_ok" = "false" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 unavailable; cannot emit fallback verified_papers.json." >&2
    echo "       Status: BLOCKED. Install python3 or restore the helper to proceed." >&2
    exit 1
  fi
  echo "      Emitting unverified candidate set with [UNVERIFIED] tags." >&2
  python3 - <<'PY'
import json
cands = json.load(open('.aris/verify-papers/candidate_papers.json'))
out = {
  'verdict': 'WARN',
  'reason_code': 'verify_papers_unavailable',
  'summary': 'verify_papers.py helper unresolved or invocation failed; all candidates tagged [UNVERIFIED] for audit visibility.',
  'papers': [dict(p, status='unverified', method='none') for p in cands],
}
with open('.aris/verify-papers/verified_papers.json', 'w') as f:
  json.dump(out, f, indent=2)
PY
fi

# 4. Read verdict + per-paper status from .aris/verify-papers/verified_papers.json;
#    surface warnings to the user.
```

**Mandatory output rules** (see
[`shared-references/citation-discipline.md`](../shared-references/citation-discipline.md)
§ Pre-Search Verification Protocol for the full contract):

- Tag every paper in the analyzed list with its status: `✅ verified (via
  arxiv|crossref|s2)` or `⚠️ UNVERIFIED (reason)` or `… verify_pending`.
- **Never silently drop unverified papers** — keep them in the output with the
  `[UNVERIFIED]` marker so the user can audit the search quality.
- Never fabricate a DOI or arXiv ID from memory. If a field is unknown, leave
  it `null` in `candidate_papers.json` — the helper will fall through to title
  search.
- If the helper returns `WARN` with `high_hallucination_rate`, surface the
  warning verbatim and recommend re-running with narrower queries.
- For papers tagged `verify_pending`, do not promote them to `verified` —
  show the pending state to the user and retry on the next session.

Optional: set `ARIS_VERIFY_EMAIL=you@institution.edu` in your shell to lift
CrossRef rate limits to the polite pool.

### Step 2: Analyze Each Paper
For **every** paper in `.aris/verify-papers/verified_papers.json`
(verified, unverified, `verify_pending`, and `error` alike — see
Retention rule above), extract:
- **Problem**: What gap does it address?
- **Method**: Core technical contribution (1-2 sentences)
- **Results**: Key numbers/claims
- **Relevance**: How does it relate to our work?
- **Source**: Where we found it (Zotero/Obsidian/local/web) — helps user know what they already have vs what's new
- **Reading artifact**: TeX source / PDF / metadata-only

When the paper came from a local source bundle, Step 2 should consume the **normalized sub-agent digest** rather than re-reading raw `.tex` in the main workflow. Map the fields as follows:
- `broad_sweep.digest.problem` or `deep_read.normalized_digest.problem` → **Problem**
- `broad_sweep.digest.method` or `deep_read.normalized_digest.method` → **Method**
- `broad_sweep.digest.results` or `deep_read.normalized_digest.results` → **Results**
- `broad_sweep.digest.relevance` or `deep_read.normalized_digest.relevance` → **Relevance**
- source origin remains **local**
- artifact comes from `artifact_used` / `normalized_digest.artifact`

Only re-open raw `.tex` or PDFs if the sub-agent explicitly reports insufficient evidence or low confidence.
- **Verification status** (one of):
  - `✅ verified (via arxiv|crossref|s2)`
  - `⚠️ UNVERIFIED (verification unavailable: helper unresolved or invocation failed)`
  - `⚠️ UNVERIFIED (searched: not found in any source)`
  - `… VERIFY_PENDING (transient API failure — retry next session)`
  - `❌ ERROR (malformed input: no arxiv, no DOI, no title)`

  Show the status in the analyzed table — never silently drop a
  paper because its status is anything other than `verified`.

### Step 3: Synthesize
Only begin this step after the local-bundle scan and any required arXiv download + re-digestion pass have completed and `papers/index.md` has been refreshed for the current run.
- Start with the prepared-report synthesis if Step 0c was used, then update it with current literature rather than rewriting from scratch
- Group papers by approach/theme
- Identify consensus vs disagreements in the field
- Find gaps that our work could fill
- Surface explicit gap statements, benchmark anchors, and open questions from the prepared reports when they still hold after verification
- If Obsidian notes exist, incorporate the user's own insights into the synthesis

### Step 4: Output
Present as a structured literature table:

```
| Paper | Venue | Method | Key Result | Relevance to Us | Source | Artifact |
|-------|-------|--------|------------|-----------------|--------|----------|
```

Plus a narrative summary of the landscape (3-5 paragraphs).

If prepared reports were used, add a short subsection before the final synthesis:
- **Prepared reports used**
- **Theme clusters carried forward**
- **Gap statements worth keeping**
- **Claims that required freshness checks**

If Zotero BibTeX was exported, include a `references.bib` snippet for direct use in paper writing.

### Step 5: Persist local artifacts and index
- The download stage itself should already save paper bundles into `papers/` (or the configured paper library) when `ARXIV_DOWNLOAD = true`; do not treat artifact persistence as optional after a successful download run
- Save or refresh `papers/index.md` whenever local or downloaded bundles were analyzed
- Append `papers/index.md` to `MANIFEST.md` using the shared output manifest protocol
- Update related work notes in project memory
- If Obsidian is available, optionally create a literature review note in the vault

### Step 6: Update Research Wiki

**Required when `research-wiki/` exists.** Skip entirely (no action, no
error) if the directory is absent. Per
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md),
this step follows the canonical ingest contract — business logic lives
in `tools/research_wiki.py`, not in this prose.

When `research-wiki/` exists, resolve `$WIKI_SCRIPT` per the canonical
chain documented in
[`shared-references/wiki-helper-resolution.md`](../shared-references/wiki-helper-resolution.md)
(Variant B — warn-and-skip):

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null)}"
WIKI_SCRIPT=".aris/tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || WIKI_SCRIPT="tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && WIKI_SCRIPT="$ARIS_REPO/tools/research_wiki.py"; }
[ -f "$WIKI_SCRIPT" ] || {
  echo "WARN: research_wiki.py not found; literature synthesis will be reported but wiki ingest will be skipped. Fix: bash tools/install_aris.sh, export ARIS_REPO, or cp <ARIS-repo>/tools/research_wiki.py tools/." >&2
  WIKI_SCRIPT=""
}
```

```
📋 Research Wiki ingest (runs once, at end of research-lit):
   [ ] 1. Predicate: `research-wiki/` exists? If no, skip this step.
   [ ] 2. If $WIKI_SCRIPT empty (helper unreachable), skip the rest of this step
          (the warning above already explains why).
   [ ] 3. For each of the top 8–12 relevant papers (arxiv IDs collected above):
          python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
              --arxiv-id <id> [--thesis "<one-line>"] [--tags <t1>,<t2>]
   [ ] 4. For each explicit relationship to an existing wiki entity,
          add an edge:
          python3 "$WIKI_SCRIPT" add_edge research-wiki/ \
              --from "paper:<slug>" --to "<target_node_id>" \
              --type <extends|contradicts|addresses_gap|inspired_by|...> \
              --evidence "<one-sentence quote or reasoning>"
   [ ] 5. Confirm papers/<slug>.md files were created (helper prints
          "Paper ingested: ..."); if any failed with a network error,
          retry or fall back to the --title/--authors/--year manual form.
```

`ingest_paper` handles slug generation, arXiv metadata fetch, dedup
(skips an existing paper by arXiv id), page rendering, `index.md`
rebuild, `query_pack.md` rebuild, and log append in a single call —
**do not manually write `papers/<slug>.md`**. If the helper is
unavailable (e.g., offline on a non-ARIS machine, or `$WIKI_SCRIPT`
empty), log the gap and let `/research-wiki sync --arxiv-ids …`
backfill later.

For non-arXiv sources (Semantic Scholar only, IEEE/ACM journals without
arXiv mirrors, blog posts), pass manual metadata instead:

```bash
python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
    --title "<full title>" --authors "A, B, C" --year <yyyy> \
    --venue "<venue>" [--external-id-doi "<doi>"] [--thesis "..."]
```

## Key Rules
- Always include paper citations (authors, year, venue)
- Distinguish between peer-reviewed and preprints
- Prefer `.tex` source over PDF text when a readable extracted source tree exists
- Fall back to PDFs cleanly when source is unavailable or unreadable
- Never let source extraction failure block the full literature review
