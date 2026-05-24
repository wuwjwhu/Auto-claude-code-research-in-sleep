---
name: idea-discovery
description: "Workflow 1: Proposal-shortlist idea discovery. Orchestrates research-lit → idea-creator → novelty-check → research-review → research-refine → experiment-plan to go from a broad research direction to a small set of top-tier proposals, pause for user choice, and only then generate the final experiment plan for the chosen proposal. Use when user says \"找idea全流程\", \"idea discovery pipeline\", \"从零开始找方向\", or wants the complete idea exploration workflow."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill
---

# Workflow 1: Proposal-Shortlist Idea Discovery Pipeline

Orchestrate a complete idea discovery workflow for: **$ARGUMENTS**

## Overview

This skill chains sub-skills into a staged pipeline:

```
/research-lit → /idea-creator → /novelty-check → /research-review → user chooses → /research-refine → /experiment-plan
  (survey)      (generate + rank)  (verify novelty)  (stress-test proposals) (hard stop)   (refine chosen)   (plan evidence)
```

The goal is **not** to lock in a weak proposal early or to run MVP experiments before the idea is mature. The goal is to produce a small set of top-tier, well-motivated, mathematically novel, technically deep proposals, harden that shortlist with novelty and reviewer scrutiny, then **stop and wait for the user to choose one**. Prefer the strongest top-tier contribution rather than the smallest intervention: compactness is a virtue only when it preserves or sharpens a theorem, formal object, provable property, or a genuinely reviewer-compelling mechanism-level insight. Only after one proposal is chosen should the workflow refine it into a final proposal and generate the experiment plan.

Final deliverables:
- `idea-stage/IDEA_REPORT.md` — ranked shortlist of hardened proposals
- `idea-stage/IDEA_CANDIDATES.md` — optional compact shortlist summary
- `refine-logs/FINAL_PROPOSAL.md` — refined version of the **chosen** proposal only
- `refine-logs/EXPERIMENT_PLAN.md` and `refine-logs/EXPERIMENT_TRACKER.md` — generated only **after** the chosen proposal is refined

## Constants

- **AUTO_PROCEED = false** — Default: do not auto-continue at checkpoints that materially change scope. The final shortlist-selection gate must wait for explicit user choice.
- **REVIEWER_MODEL = `gpt-5.5`** — Model used via `codex exec`. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`). Passed to sub-skills.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **ARXIV_DOWNLOAD = true** — By default, `/research-lit` downloads the top relevant arXiv reading artifacts during Phase 1: PDF plus source archive / extracted source tree when available. Passed through to `/research-lit`.
- **COMPACT = false** — When `true`, generate compact summary files for short-context models and session recovery. Writes `idea-stage/IDEA_CANDIDATES.md` (top 2-3 proposals only) at the end of the shortlist stage.
- **REF_PAPER = false** — Reference paper to base ideas on. Accepts: local PDF path, arXiv URL, or any paper URL. When set, the paper is summarized first (`idea-stage/REF_PAPER_SUMMARY.md`), then idea generation uses it as context. Combine with `base repo` for "improve this paper with this codebase" workflows.
- **REPORT = `auto`** — Prepared deep research markdown input for Phase 1. Accepts: `auto`, `none`, or a specific markdown path such as `deep-research/deep-research-report.md`.

> 💡 These are defaults. Override by telling the skill, e.g., `/idea-discovery "topic" — ref paper: https://arxiv.org/abs/2406.04329`, `/idea-discovery "topic" — report: deep-research/deep-research-report.md`, or `/idea-discovery "topic" — compact: true`.

## Pipeline

### Phase 0: Load Research Brief (if available)

Before starting any other phase, check for a detailed research brief in the project:

1. Look for `RESEARCH_BRIEF.md` in the project root (or path passed as `$ARGUMENTS`)
2. If found, read it and extract:
   - Problem statement and context
   - Constraints (compute, data, timeline, venue)
   - What the user already tried / what didn't work
   - Domain knowledge and non-goals
   - Existing results (if any)
3. Use this as the primary context for all subsequent phases — it replaces the one-line prompt
4. If both `RESEARCH_BRIEF.md` and a one-line `$ARGUMENTS` exist, merge them (brief takes priority for details, argument sets the direction)

If no brief exists, proceed normally with `$ARGUMENTS` as the research direction.

> 💡 Create a brief from the template: `cp templates/RESEARCH_BRIEF_TEMPLATE.md RESEARCH_BRIEF.md`

### Phase 0.25: Prepared Deep Research Reports (when REPORT is not `none`)

Before Phase 1, treat prepared markdown reports under `deep-research/` as additional landscape context.

Precedence is:
1. `RESEARCH_BRIEF.md` defines the actual problem, constraints, non-goals, and prior attempts
2. `REF_PAPER` defines the paper-specific seed when present
3. prepared reports provide prior synthesized landscape context
4. `/research-lit` still performs fresh search afterward to verify freshness and catch missed work

Behavior:
- If `— report: <path>` is provided, forward that exact report choice into `/research-lit`
- If `— report: auto` is used (default), let `/research-lit` auto-detect the most relevant markdown reports in `deep-research/`
- If `— report: none` is used, skip prepared reports entirely and use the older workflow

Do not treat prepared reports as a replacement for literature review. Their job is to improve the starting point for `/research-lit`, which then produces the normalized landscape summary used by later phases.

### Phase 0.5: Reference Paper Summary (when REF_PAPER is set)

**Skip entirely if `REF_PAPER` is `false`.**

Summarize the reference paper before searching the literature:

1. **If arXiv URL** (e.g., `https://arxiv.org/abs/2406.04329`):
   - Invoke `/arxiv "ARXIV_ID" — download` to fetch the PDF
   - Read the first 5 pages (title, abstract, intro, method overview)

2. **If local PDF path** (e.g., `papers/reference.pdf`):
   - Read the PDF directly (first 5 pages)

3. **If other URL**:
   - Fetch and extract content via WebFetch

4. **Generate `idea-stage/REF_PAPER_SUMMARY.md`** with:
   - paper title / venue / authors
   - what they did
   - key results
   - limitations and open questions
   - promising improvement directions
   - codebase mapping if a base repo is also provided

**🚦 Checkpoint:** Present the summary to the user:

```
📄 Reference paper summarized:
- Title: [title]
- Key limitation: [main gap]
- Improvement directions: [2-3 bullets]

Proceeding to literature survey with this as context.
```

Phase 1 and Phase 2 will use `idea-stage/REF_PAPER_SUMMARY.md` as additional context — `/research-lit` searches for related and competing work, `/idea-creator` generates ideas that build on or improve the reference paper.

### Phase 1: Literature Survey

Invoke `/research-lit` to map the research landscape. Idea discovery is exactly the place where Gemini's AI-driven broad coverage adds value, so include `gemini` as a source by default unless the user already specified an explicit `— sources:` directive in their idea-discovery invocation:

```
# If $ARGUMENTS already contains "— sources:", pass through unchanged
# (the user is in control of source selection):
/research-lit "$ARGUMENTS"

# Otherwise (the common case), include gemini explicitly for broader discovery:
/research-lit "$ARGUMENTS" — sources: all, gemini
```

If `REPORT` was set explicitly, forward it into `/research-lit`. Otherwise rely on `/research-lit` auto-detection in `deep-research/`.

If `gemini-cli` is not installed, `/research-lit` skips the Gemini source gracefully with a warning — no break to the pipeline. Users who want to force-disable Gemini in idea-discovery can pass `/idea-discovery "topic" — sources: all` explicitly (which becomes the literal source list, no auto-injection).

**What this does:**
- Read prepared deep-research markdown first when available
- Search arXiv, Google Scholar, Semantic Scholar for recent papers
- Download top-ranked arXiv paper artifacts into `papers/` when `ARXIV_DOWNLOAD = true`: PDFs plus source archives / extracted source trees when available
- Use `/research-lit`'s source-first local paper ingestion path when extracted `.tex` bundles are available
- Delegate bounded `.tex` digestion to sub-agents that return compact digests rather than pulling raw source into the main context
- Build and refresh `papers/index.md` so each ingested paper records its PDF path, main TeX path, and concise summary fields for later reuse
- Plus Gemini-driven broad discovery (sub-problem decomposition, naming variants, alias coverage) when `gemini-cli` is available
- Complete the literature stage only after any newly downloaded/relevant bundles have been digested and the index is refreshed for downstream reuse
- Build a landscape map: sub-directions, approaches, open problems
- Identify structural gaps and recurring limitations
- Output a normalized literature summary for later phases

Before presenting this checkpoint, verify that the literature phase actually executed the required artifact-ingestion path when `ARXIV_DOWNLOAD = true`: there should either be newly materialized paper artifacts under `papers/` plus refreshed `papers/index.md`, or an explicit report that no relevant arXiv IDs were available / downloads were attempted but failed.

**🚦 Checkpoint:** Present the landscape summary to the user. Ask:

```
📚 Literature survey complete. Here's what I found:
- [key findings, gaps, open problems]

Does this match your understanding? Should I adjust the scope before generating proposals?
```

- **User approves** → proceed to Phase 2 with best direction.
- **User requests changes** (e.g., "focus more on X", "ignore Y", "too broad") → refine the search with updated queries, re-run `/research-lit` with adjusted scope, and present again.
- **Artifact-ingestion check fails** → do not proceed. Go back to `/research-lit` and finish the required download + local-ingestion path first.

### Phase 2: Proposal Generation + Conceptual Filtering

Invoke `/idea-creator` with the landscape context (and `idea-stage/REF_PAPER_SUMMARY.md` if available):

```
/idea-creator "$ARGUMENTS"
```

**What this does:**
- If `idea-stage/REF_PAPER_SUMMARY.md` exists, include it as context — ideas should build on, improve, or extend the reference paper
- Read `papers/index.md` first when available so brainstorming is anchored to the local paper library and its recorded PDF/main-TeX paths plus concise paper digests
- If Phase 1 used prepared reports, rely on the normalized literature synthesis rather than rereading raw `deep-research/*.md`
- Brainstorm 8-12 concrete proposals via GPT-5.5 xhigh
- Filter by problem importance, mathematical/formal substance, technical depth, mechanism clarity, differentiation from closest prior work, and paper-worthiness
- Reject proposals that are merely clean/elegant without a theorem, formal object, provable claim, or comparably deep mechanism-level contribution
- Reduce to a shortlist of 2-3 strong proposals
- Output a proposal-first `idea-stage/IDEA_REPORT.md`

**🚦 Checkpoint:** Present the provisional shortlist to the user:

```
💡 Generated X proposals and filtered to Y strong candidates. Current shortlist:

1. [Proposal 1] — [one-line novelty thesis]
2. [Proposal 2] — [one-line novelty thesis]
3. [Proposal 3] — [one-line novelty thesis]

I will now harden these with novelty-check and reviewer scrutiny before asking you to choose one.
```

### Phase 3: Deep Novelty Verification

For each shortlisted proposal, run a targeted novelty check:

```
/novelty-check "[shortlisted proposal 1 description]"
/novelty-check "[shortlisted proposal 2 description]"
```

**What this does:**
- Builds on the paper discovery and first-pass reading already done by `/research-lit`
- Starts from `papers/index.md` when available to recover the local prior-work map plus each paper's `main_tex_path` / `pdf_path`
- Runs proposal-specific freshness checks for the closest overlapping work
- Cross-verifies with GPT-5.5 xhigh
- Checks for concurrent work (last 3-6 months)
- Identifies the closest existing work and the remaining differentiation points

**What this should not do by default:**
- Re-run the broad literature sweep already done in Phase 1
- Replace `research-lit` as the main paper download / source-reading stage
- Ignore the paper index and jump straight to raw PDFs when `main_tex_path` or other indexed artifacts already exist

**Update `idea-stage/IDEA_REPORT.md`** with deep novelty results. Eliminate any proposal whose core mechanism is already covered by existing work.

### Phase 4: External Critical Review

For the surviving shortlisted proposals, get brutal feedback:

```
/research-review "[shortlisted proposal description + novelty findings]"
```

**This phase requires an explicit `/research-review` execution.** Do not treat reviewer-style objections generated earlier inside `/idea-creator`, `/novelty-check`, or ad hoc analysis as a substitute for this step. The workflow is not ready for the shortlist checkpoint until `/research-review` has actually run on the surviving proposals.

**What this does:**
- GPT-5.5 xhigh acts as a senior reviewer (NeurIPS/ICML level)
- Starts from `papers/index.md` when available so review is anchored to the local prior-work set before selectively reopening only the most critical comparator papers
- Uses `main_tex_path` first and `pdf_path` second when a critical prior paper must be read directly
- Scores conceptual sharpness, technical depth, mechanism clarity, and contribution quality
- Identifies the strongest reviewer objections and missing technical detail
- Specifies what evidence would later be required without forcing a full experiment plan yet

**Update `idea-stage/IDEA_REPORT.md`** with reviewer feedback and revised rankings.

### Phase 4.5: Final Shortlist Checkpoint — User Choice Required

Before presenting the shortlist, verify that Phase 4 actually ran as an explicit `/research-review` step for the surviving proposals and that `idea-stage/IDEA_REPORT.md` has been updated with those reviewer findings. If not, do not present the shortlist yet — go back and run Phase 4 first.

Present the final hardened shortlist to the user:

```
📋 Proposal shortlist ready. Top candidates:

1. [Proposal 1]
   - Novelty: [summary]
   - Technical depth: [summary]
   - Mathematical/formal substance: [summary]
   - Why a skeptical top-tier reviewer should care: [summary]
   - Strongest objection: [summary]

2. [Proposal 2]
   - Novelty: [summary]
   - Technical depth: [summary]
   - Mathematical/formal substance: [summary]
   - Why a skeptical top-tier reviewer should care: [summary]
   - Strongest objection: [summary]

3. [Proposal 3]
   - Novelty: [summary]
   - Technical depth: [summary]
   - Mathematical/formal substance: [summary]
   - Why a skeptical top-tier reviewer should care: [summary]
   - Strongest objection: [summary]

Please choose one proposal, request regeneration with new constraints, or stop here.
```

**⛔ STOP HERE and wait for user response.** Do **not** auto-proceed to proposal refinement or experiment planning from this gate.

Options:
- Reply **with a proposal number/title** → proceed to Phase 5 with that proposal
- Reply with **adjustments** → update the constraints and regenerate the shortlist
- Reply **"stop"** → save the shortlist artifacts and end the workflow

Do not reinterpret a user choice here. If the user explicitly chooses Proposal 2 or 3 instead of the top-ranked recommendation, carry forward the user's selected proposal rather than auto-substituting the recommended one.

### Phase 5: Refine the Chosen Proposal

After the user chooses one proposal, refine it into a concrete method:

```
/research-refine "[chosen proposal description + novelty findings + reviewer feedback]"
```

**What this does:**
- Freeze a **Problem Anchor** to prevent scope drift
- Iteratively refine the method via GPT-5.5 review
- Produce a focused, paper-worthy final proposal
- Output: `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/REVIEW_SUMMARY.md`, `refine-logs/REFINEMENT_REPORT.md`

**🚦 Checkpoint:** Present the refined proposal summary:

```
🔬 Chosen proposal refined:
- Problem anchor: [anchored problem]
- Method thesis: [one sentence]
- Dominant contribution: [what's new]
- Key reviewer risk still remaining: [risk]

Ready to generate the final experiment plan?
```

- **User approves** → proceed to Phase 5.5.
- **User requests changes** → pass feedback to `/research-refine` for another round.

### Phase 5.5: Final Experiment Plan for the Chosen Proposal

Only after the chosen proposal is refined and accepted, generate the final experiment plan:

```
/experiment-plan "[refine-logs/FINAL_PROPOSAL.md]"
```

**What this does:**
- Freeze the claims that the final paper must defend
- Generate a claim-driven experiment roadmap with ablations, budgets, and run order
- Output: `refine-logs/EXPERIMENT_PLAN.md`, `refine-logs/EXPERIMENT_TRACKER.md`

### Phase 6: Final Report

Finalize `idea-stage/IDEA_REPORT.md` with all accumulated information:

```markdown
# Idea Discovery Report

**Direction**: $ARGUMENTS
**Date**: [today]
**Pipeline**: research-lit → idea-creator → novelty-check → research-review → user choice → research-refine → experiment-plan

## Executive Summary
[2-3 sentences: best shortlisted proposals, chosen proposal, recommended next step]

## Literature Landscape
[from Phase 1]

## Ranked Proposal Shortlist
[from Phase 2, updated with Phase 3-4 results]

### Proposal 1: [title]
- Core thesis:
- Novelty: [closest work + true delta]
- Technical depth:
- Strongest reviewer objection:
- Status: SHORTLISTED / CHOSEN / ELIMINATED

### Proposal 2: [title]
...

## Chosen Proposal
- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Next Steps
- [ ] /run-experiment to deploy experiments from the chosen plan
- [ ] /auto-review-loop to iterate after first full results
- [ ] Or invoke /research-pipeline for the complete end-to-end flow
```

### Phase 6.5: Write Compact Files (when COMPACT = true)

**Skip entirely if `COMPACT` is `false`.**

Write `idea-stage/IDEA_CANDIDATES.md` — a lean summary of the top 2-3 surviving proposals:

```markdown
# Idea Candidates

| # | Proposal | Novelty | Technical Depth | Reviewer Score | Status |
|---|----------|---------|-----------------|----------------|--------|
| 1 | [title] | [summary] | [summary] | X/10 | SHORTLISTED |
| 2 | [title] | [summary] | [summary] | X/10 | CHOSEN / BACKUP |
| 3 | [title] | [summary] | [summary] | X/10 | ELIMINATED |

## Chosen Proposal
- Thesis: [one sentence]
- Key differentiator: [one sentence]
- Next step: /experiment-plan
```

This file is intentionally small so downstream skills and session recovery can read it without loading the full `idea-stage/IDEA_REPORT.md`.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- **Do not run MVP experiments during idea discovery.** This workflow is proposal-first, not pilot-first.
- **Do not auto-choose the final proposal.** The shortlist-selection gate must wait for explicit user choice.
- **Proposal quality outranks cheap executability.** Rank by novelty, technical depth, mechanism clarity, and paper-worthiness.
- **Kill weak proposals early.** It is better to reject shallow proposals before implementation than to refine them into bigger but still weak plans.
- **Document dead ends.** Eliminated proposals still save future time.
- **Be honest with the reviewer.** Include the actual weaknesses, missing detail, and prior-work risks in the review prompt.
- **Feishu notifications are optional.** If `~/.claude/feishu.json` exists, send `checkpoint` at each phase transition and `pipeline_done` at final report. If absent/off, skip silently.

## Composing with Workflow 2

After this pipeline produces a chosen/refined proposal plus experiment plan:

```
/idea-discovery "direction"         ← you are here (Workflow 1)
/run-experiment                     ← deploy experiments from the chosen plan
/auto-review-loop "chosen idea"     ← Workflow 2: iterate after results arrive

Or use /research-pipeline for the full end-to-end flow.
```
