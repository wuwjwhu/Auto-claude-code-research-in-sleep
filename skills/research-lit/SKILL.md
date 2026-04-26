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
- **If `— sources:` is specified**: Only search the listed sources (comma-separated). Valid values: `zotero`, `obsidian`, `local`, `web`, `semantic-scholar`, `deepxiv`, `exa`, `all`.
- **If not specified**: Default to `all` — search every available source in priority order (`semantic-scholar`, `deepxiv`, and `exa` are **excluded** from `all`; they must be explicitly listed).

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
```

### Source Table

| Priority | Source | ID | How to detect | What it provides |
|----------|--------|----|---------------|-----------------|
| 1 | **Zotero** (via MCP) | `zotero` | Try calling any `mcp__zotero__*` tool — if unavailable, skip | Collections, tags, annotations, PDF highlights, BibTeX, semantic search |
| 2 | **Obsidian** (via MCP) | `obsidian` | Try calling any `mcp__obsidian-vault__*` tool — if unavailable, skip | Research notes, paper summaries, tagged references, wikilinks |
| 3 | **Prepared markdown reports** | `report` | `Glob: deep-research/*.md` or explicit `— report: <path>` | Precomputed deep research synthesis: framing, theme clusters, gap statements, benchmarks, open questions |
| 4 | **Local paper bundles** | `local` | `Glob: papers/**/*.pdf, papers/**/*.src.tar.gz, papers/**/*.tex, literature/**/*.pdf, literature/**/*.src.tar.gz, literature/**/*.tex` | Extracted LaTeX source when available, otherwise source archive / PDF fallback |
| 5 | **Web search** | `web` | Always available (WebSearch) | arXiv, Semantic Scholar, Google Scholar |
| 6 | **Semantic Scholar API** | `semantic-scholar` | `tools/semantic_scholar_fetch.py` exists | Published venue papers (IEEE, ACM, Springer) with structured metadata: citation counts, venue info, TLDR. **Only runs when explicitly requested** via `— sources: semantic-scholar` or `— sources: web, semantic-scholar` |
| 7 | **DeepXiv CLI** | `deepxiv` | `tools/deepxiv_fetch.py` and installed `deepxiv` CLI | Progressive paper retrieval: search, brief, head, section, trending, web search. **Only runs when explicitly requested** via `— sources: deepxiv` or `— sources: all, deepxiv` |
| 8 | **Exa Search** | `exa` | `tools/exa_search.py` and installed `exa-py` SDK | AI-powered broad web search with content extraction (highlights, text, summaries). Covers blogs, docs, news, companies, and research papers beyond arXiv/S2. **Only runs when explicitly requested** via `— sources: exa` or `— sources: all, exa` |

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

Locate the fetch script and search arXiv directly:
```bash
# Prefer the helper shipped inside the skill installation
SCRIPT="$HOME/.claude/skills/arxiv/arxiv_fetch.py"
# Fall back to the project-local copy when running from this repo
[ ! -f "$SCRIPT" ] && SCRIPT="skills/arxiv/arxiv_fetch.py"
# Last fallback: top-level project helper
[ ! -f "$SCRIPT" ] && SCRIPT="tools/arxiv_fetch.py"

# Search arXiv API for structured results (title, abstract, authors, categories)
python3 "$SCRIPT" search "QUERY" --max 10
```

If `arxiv_fetch.py` is not found in any of those locations, report this clearly and treat it as a setup failure for source-first arXiv ingestion. Do **not** silently degrade into a WebSearch-only path when `ARXIV_DOWNLOAD = true`, because the paper-bundle download and source-first reading stages depend on the helper being available.

The arXiv API returns structured metadata (title, abstract, full author list, categories, dates) — richer than WebSearch snippets. Merge these results with the other sources and de-duplicate.

**Semantic Scholar API search** (only when `semantic-scholar` is in sources):

When the user explicitly requests `— sources: semantic-scholar` (or `— sources: web, semantic-scholar`), search for published venue papers beyond arXiv.

**DeepXiv search** (only when `deepxiv` is in sources)** and **Exa search** (only when `exa` is in sources)** remain unchanged from the current workflow.

**Required arXiv artifact download stage** (default-on when `ARXIV_DOWNLOAD = true`):

After all sources are searched and papers are ranked by relevance, the expected execution order is:
1. download top-ranked arXiv bundles into `papers/`
2. re-scan the augmented local paper library
3. digest the newly available bundles through the same source-first sub-agent path
4. refresh `papers/index.md`
5. only then finalize the literature synthesis

```bash
# Download top N most relevant arXiv paper bundles
python3 "$SCRIPT" download ARXIV_ID --dir papers/
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

### Step 2: Analyze Each Paper
For each relevant paper (from all sources), extract:
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

```
📋 Research Wiki ingest (runs once, at end of research-lit):
   [ ] 1. Predicate: `research-wiki/` exists? If no, skip this step.
   [ ] 2. For each of the top 8–12 relevant papers (arxiv IDs collected above):
          python3 tools/research_wiki.py ingest_paper research-wiki/ \
              --arxiv-id <id> [--thesis "<one-line>"] [--tags <t1>,<t2>]
   [ ] 3. For each explicit relationship to an existing wiki entity,
          add an edge:
          python3 tools/research_wiki.py add_edge research-wiki/ \
              --from "paper:<slug>" --to "<target_node_id>" \
              --type <extends|contradicts|addresses_gap|inspired_by|...> \
              --evidence "<one-sentence quote or reasoning>"
   [ ] 4. Confirm papers/<slug>.md files were created (helper prints
          "Paper ingested: ..."); if any failed with a network error,
          retry or fall back to the --title/--authors/--year manual form.
```

`ingest_paper` handles slug generation, arXiv metadata fetch, dedup
(skips an existing paper by arXiv id), page rendering, `index.md`
rebuild, `query_pack.md` rebuild, and log append in a single call —
**do not manually write `papers/<slug>.md`**. If the helper is
unavailable (e.g., offline on a non-ARIS machine), log the gap and let
`/research-wiki sync --arxiv-ids …` backfill later.

For non-arXiv sources (Semantic Scholar only, IEEE/ACM journals without
arXiv mirrors, blog posts), pass manual metadata instead:

```
python3 tools/research_wiki.py ingest_paper research-wiki/ \
    --title "<full title>" --authors "A, B, C" --year <yyyy> \
    --venue "<venue>" [--external-id-doi "<doi>"] [--thesis "..."]
```

## Key Rules
- Always include paper citations (authors, year, venue)
- Distinguish between peer-reviewed and preprints
- Prefer `.tex` source over PDF text when a readable extracted source tree exists
- Fall back to PDFs cleanly when source is unavailable or unreadable
- Never let source extraction failure block the full literature review
