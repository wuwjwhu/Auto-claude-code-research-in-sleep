---
name: idea-creator
description: Generate and rank research proposals given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Grep, Glob, WebSearch, WebFetch, Agent
---

# Research Idea Creator

Generate publishable research proposals for: $ARGUMENTS

## Overview

Given a broad research direction from the user, systematically generate, validate, and rank concrete research proposals. This skill composes with `/research-lit`, `/novelty-check`, and `/research-review` to form a complete idea discovery pipeline.

The goal is **not** to pick whatever is easiest to pilot. The goal is to surface a small set of proposals that are:
- well-motivated
- mathematically or conceptually novel
- technically deep
- clearly differentiated from the closest prior work
- strong enough to deserve later refinement into a paper-worthy method

## Constants

- **REVIEWER_MODEL = `gpt-5.4`** — Model used via `codex exec` for brainstorming and review. Must be an OpenAI model (e.g., `gpt-5.4`, `o3`, `gpt-4o`).
- **REVIEWER_BACKEND = `codex`** — Default: `codex exec` (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.

## Workflow

### Phase 0: Load Research Wiki (if active)

**Skip this phase entirely if `research-wiki/` does not exist.**

```
if research-wiki/query_pack.md exists AND is less than 7 days old:
    Read query_pack.md and use it as initial landscape context:
    - Treat listed gaps as priority search seeds
    - Treat failed ideas as a banlist (do NOT regenerate similar ideas)
    - Treat top papers as known prior work (do not re-search them)
    Still run Phase 1 below for papers from the last 3-6 months (wiki may be stale)
else if research-wiki/ exists but query_pack.md is stale or missing:
    python3 tools/research_wiki.py rebuild_query_pack research-wiki/
    Then read query_pack.md as above
```

### Phase 1: Landscape Survey (5-10 min)

Map the research area to understand what exists and where the gaps are.

If this skill is being called from `/idea-discovery`, treat the Phase 1 output from `/research-lit` as the primary landscape input.

1. **Use normalized upstream synthesis first**: If `/research-lit` already incorporated prepared deep-research markdown reports, use its normalized synthesis as the main landscape map instead of rereading raw `deep-research/*.md`.

2. **Scan local paper library when needed**: Check `papers/` and `literature/` in the project directory for existing PDFs only to fill gaps or validate missing details. Read first 3 pages of relevant papers to build a baseline understanding before searching online.

3. **Search recent literature** using WebSearch when the upstream synthesis is missing, stale, or incomplete:
   - Top venues in the last 2 years (NeurIPS, ICML, ICLR, ACL, EMNLP, etc.)
   - Recent arXiv preprints (last 6 months)
   - Use 5+ different query formulations
   - Read abstracts and introductions of the top 10-15 papers

4. **Build a landscape map**:
   - Group papers by sub-direction / approach
   - Identify what has been tried and what hasn't
   - Carry forward explicit theme clusters and benchmark anchors from prepared-report-derived synthesis when still supported
   - Note recurring limitations mentioned in "Future Work" sections
   - Flag any open problems explicitly stated by multiple papers

5. **Identify structural gaps**:
   - Prefer explicit gap statements and unresolved contradictions surfaced by `/research-lit`
   - Methods that work in domain A but haven't been tried in domain B
   - Contradictory findings between papers (opportunity for resolution)
   - Assumptions that everyone makes but nobody has tested
   - Scaling regimes that haven't been explored
   - Diagnostic questions that nobody has asked

### Phase 2: Proposal Generation (brainstorm with external LLM)

Use the external LLM via `codex exec` for divergent thinking:

```bash
codex exec "$(cat <<'PROMPT'
You are a senior ML researcher brainstorming top-tier research proposals.

Research direction: [user's direction]

Here is the current landscape:
[paste landscape map from Phase 1]

If the landscape came from `/research-lit` with prepared deep-research markdown, trust its normalized theme clusters, benchmark anchors, and explicit gap statements more than raw narrative prose.

Key gaps identified:
[paste gaps from Phase 1]

Generate 8-12 concrete research proposals. For each proposal, provide:
1. One-sentence thesis
2. Problem anchor: what bottleneck or gap does it really solve?
3. Core technical mechanism
4. Why it is mathematically, conceptually, or technically novel
5. Closest prior work and the true delta
6. Expected contribution type: new method / theoretical result / empirical finding / diagnostic
7. Strongest reviewer objection
8. Evidence that would eventually be needed to defend the claim
9. Risk level: LOW / MEDIUM / HIGH
10. Estimated effort: days / weeks / months

Prioritize proposals that are:
- top-venue worthy if executed well
- technically deep rather than superficially clever
- not "apply X to Y" unless the application reveals a genuinely new mechanism or principle
- differentiated from the strongest nearby prior work
- feasible enough to pursue later, without letting cheap testability dominate the ranking

Be creative but grounded. A great proposal is one with a crisp mechanism-level thesis, a legible novelty story, and enough depth that a strong reviewer would care.
PROMPT
)" --skip-git-repo-check 2>&1
```

Save the full raw reviewer output for follow-up rounds.

### Phase 3: First-Pass Filtering

For each generated proposal, quickly evaluate:

1. **Novelty / differentiation**
   - Is the mechanism genuinely different from the closest work?
   - Is the proposal more than a renamed combination of familiar parts?

2. **Technical depth**
   - Is there a real mechanism, formulation, theorem, or principle?
   - Would a reviewer see a substantive contribution rather than a thin tweak?

3. **Paper-worthiness**
   - If executed well, would this make a compelling top-tier paper?
   - Does the answer matter regardless of whether the empirical outcome is strongly positive or mixed?

4. **Feasibility check**
   - Data availability
   - Implementation complexity
   - Whether the proposal is actionable under realistic resources
   - Feasibility is a constraint, not the primary ranker

5. **Evidence hygiene**
   - If a claim came only from prepared report prose and not from current literature verification, treat it as a brainstorming seed, not as proof of novelty or importance.

Eliminate proposals that fail any of these. Typically 8-12 proposals reduce to 3-5.

### Phase 4: Deep Validation (for top proposals)

For each surviving proposal, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + GPT-5.4 cross-verification) for each proposal.

2. **Critical review**: Use GPT-5.4 via `codex exec` (same thread):
   ```
   Here are our top proposals after filtering:
   [paste surviving proposals with novelty check results]

   For each, play devil's advocate:
   - What's the strongest objection a reviewer would raise?
   - Where is the mechanism still underspecified?
   - How would you rank these for a top venue submission?
   - Which 2-3 would you actually keep as a final shortlist?
   ```

3. **Combine rankings**: Merge your assessment with GPT-5.4's ranking. Select the top 2-3 proposals for the final shortlist.

### Phase 5: Output — Ranked Proposal Report

Write a structured report to `idea-stage/IDEA_REPORT.md`:

```markdown
# Research Idea Report

**Direction**: [user's research direction]
**Generated**: [date]
**Proposals evaluated**: X generated → Y survived filtering → Z shortlisted

## Landscape Summary
[3-5 paragraphs on the current state of the field]

## Ranked Proposal Shortlist

### Proposal 1: [title]
- **Thesis**: [one sentence]
- **Problem anchor**: [what bottleneck it addresses]
- **Core mechanism**: [technical summary]
- **Novelty**: X/10 — closest work: [paper] — true delta: [difference]
- **Technical depth**: [why it is not shallow]
- **Feasibility**: [data / implementation / resource notes]
- **Risk**: LOW/MEDIUM/HIGH
- **Contribution type**: method / theory / empirical finding / diagnostic
- **Reviewer's likely objection**: [strongest counterargument]
- **Evidence later needed**: [what would need to be shown eventually]
- **Why we should keep it**: [1-2 sentences]

### Proposal 2: [title]
...

## Eliminated Proposals (for reference)
| Proposal | Reason eliminated |
|----------|-------------------|
| ... | Already done by [paper] |
| ... | Too shallow / weak mechanism |
| ... | Interesting but not paper-worthy |

## Suggested Next Step
- Present the shortlist to the user
- Run `/novelty-check` and `/research-review` on the shortlisted proposals if not already done
- Ask the user to choose one proposal for refinement
```

### Phase 6: Write Ideas to Research Wiki (if active)

**Skip this phase entirely if `research-wiki/` does not exist.**

This is critical for spiral learning — without it, `ideas/` stays empty and re-ideation has no memory.

```
if research-wiki/ exists:
    for each proposal in shortlisted_proposals + eliminated_proposals:
        1. Create page: research-wiki/ideas/<idea_id>.md
           - node_id: idea:<id>
           - stage: proposed (or: archived)
           - outcome: unknown
           - based_on: [paper:<slug>, ...]
           - target_gaps: [gap:<id>, ...]
           - Include: thesis, problem anchor, proposed mechanism, expected contribution

        2. Add edges:
           python3 tools/research_wiki.py add_edge research-wiki/ --from "idea:<id>" --to "paper:<slug>" --type inspired_by --evidence "..."
           python3 tools/research_wiki.py add_edge research-wiki/ --from "idea:<id>" --to "gap:<id>" --type addresses_gap --evidence "..."

    Rebuild query pack:
        python3 tools/research_wiki.py rebuild_query_pack research-wiki/
    Log:
        python3 tools/research_wiki.py log research-wiki/ "idea-creator wrote N proposals (M shortlisted, K eliminated)"
```

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- The user provides a DIRECTION, not an idea. Your job is to generate the proposals.
- Quantity first, quality second: brainstorm broadly, then filter ruthlessly.
- Do not rank proposals by how cheaply they can be piloted. Rank them by novelty, depth, mechanism clarity, and paper-worthiness.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated proposals in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., "NLP", "computer vision", "reinforcement learning"), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the problem, domain, and constraint.

## Composing with Other Skills

After this skill produces the ranked shortlist:
```
/idea-creator "direction"     → ranked proposal shortlist
/novelty-check "top proposal" → deep novelty verification
/research-review "top proposal" → external critical feedback
/research-refine              → refine the chosen proposal
/experiment-plan              → generate the final experiment roadmap after proposal selection
```

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
