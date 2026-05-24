---
name: novelty-check
description: Verify research idea novelty against recent literature. Use when user says "查新", "novelty check", "有没有人做过", "check novelty", or wants to verify a research idea is novel before implementing.
argument-hint: [method-or-idea-description]
allowed-tools: WebSearch, WebFetch, Grep, Read, Glob
---

# Novelty Check Skill

Check whether a proposed method/idea has already been done in the literature: **$ARGUMENTS**

This skill can be run on a **single proposal** or repeated across a **shortlist of proposals** during idea discovery.

## Constants

- REVIEWER_MODEL = `gpt-5.5` — Model used via `codex exec`. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`)

## Instructions

Given a method description, systematically verify its novelty:

### Phase A: Extract Key Claims
1. Read the user's method description
2. Identify 3-5 core technical claims that would need to be novel:
   - What is the method?
   - What problem does it solve?
   - What is the mechanism?
   - What makes it different from obvious baselines?
3. If the proposal is mathematically or conceptually motivated, explicitly extract the mechanism-level novelty claims rather than checking only surface keywords.

### Phase B: Proposal-Specific Freshness and Overlap Check
This skill is **not** the main literature-ingestion stage. By the time it runs inside `idea-discovery`, `/research-lit` should already have done the heavy lifting: broad paper discovery, artifact download, source-first first-pass reading, and shortlist construction.

Before running freshness search, read `papers/index.md` when available and use it as the canonical local prior-work map for this proposal. Recover each candidate paper's `main_tex_path`, `pdf_path`, `brief_summary`, `problem`, `method`, `result`, and `takeaway` from the index instead of rebuilding the literature map from scratch.

For EACH core claim, do only the narrower proposal-specific checks needed to stress-test novelty:

1. **Freshness search** (via `WebSearch`):
   - Search arXiv, Google Scholar, Semantic Scholar for the closest overlapping recent work
   - Use specific technical terms from the claim
   - Try at least 3 different query formulations per claim
   - Include year filters for 2024-2026
   - Prioritize concurrent or very recent work that could invalidate the proposal's differentiation

2. **Closest-work confirmation**:
   - Check against the strongest nearby papers already surfaced by `/research-lit`
   - Start from the closest candidates already indexed in `papers/index.md` when available
   - Add only the missing closest papers or fresher overlaps that matter for this proposal

3. **Targeted reading only**:
   - Read abstracts, related work, or the most relevant sections of the closest papers
   - For critical confirmation reads, prefer the indexed `main_tex_path`; fall back to the indexed `pdf_path` only when TeX is absent or unreadable
   - Do not re-run a broad literature sweep here unless the prior literature stage was clearly insufficient

### Phase C: Cross-Model Verification
Call REVIEWER_MODEL via `codex exec` (`codex exec`) with xhigh reasoning:
```
config: {"model_reasoning_effort": "xhigh"}
```
Prompt should include:
- The proposed method description
- All papers found in Phase B
- Ask: "Is this method novel? What is the closest prior work? What is the delta?"
- If relevant, also ask: "Is the mathematical or conceptual novelty real, or is this mostly a rephrasing of existing mechanisms?"
- Also ask: "Is the novelty substantive enough for a top-tier paper, or is it still likely to be seen as incremental even if the overlap is not exact?"
- Also ask: "If the idea is compact, what theorem, formal object, provable property, or comparably deep mechanism-level insight actually justifies that compactness?"

### Phase D: Novelty Report
Output a structured report:

```markdown
## Novelty Check Report

### Proposed Method
[1-2 sentence description]

### Core Claims
1. [Claim 1] — Novelty: HIGH/MEDIUM/LOW — Closest: [paper]
2. [Claim 2] — Novelty: HIGH/MEDIUM/LOW — Closest: [paper]
...

### Closest Prior Work
| Paper | Year | Venue | Overlap | Key Difference |
|-------|------|-------|---------|----------------|

### Overall Novelty Assessment
- Score: X/10
- Recommendation: PROCEED / PROCEED WITH CAUTION / ABANDON
- Key differentiator: [what makes this unique, if anything]
- Risk: [what a reviewer would cite as prior work]
- Substance verdict: THIN / ADEQUATE / STRONG
- If compact, what formal or mechanism-level fact justifies that compactness?
- If still weak, would a reviewer likely call it incremental even with perfect execution?

### Suggested Positioning
[How to frame the contribution to maximize novelty perception without overstating shallow novelty]
```

### Important Rules
- Be BRUTALLY honest — false novelty claims waste months of research time
- "Applying X to Y" is NOT novel unless the application reveals surprising insights
- A proposal can be novel in literal overlap terms and still be too thin for a top-tier paper; say that explicitly when it happens
- Do not over-reward compactness unless it comes with a theorem, formal object, provable property, or similarly deep mechanism-level contribution
- Check both the method AND the experimental setting for novelty
- If the method is not novel but the FINDING would be, say so explicitly
- Always check the most recent 6 months of arXiv — the field moves fast
- When used on a shortlist, compare each proposal against the closest work on its own mechanism, not just against the other shortlisted proposals
- **Anti-hallucination for Closest Prior Work.** Every paper in the prior-work table must pass pre-search verification via `verify_papers.py` (canonical name resolved per [`shared-references/integration-contract.md`](../shared-references/integration-contract.md) §2; 3-layer arXiv / CrossRef / Semantic Scholar fallback inside the helper itself). Policy D1 (primary + degraded-output fallback): if the helper is unresolved **or** its invocation fails, tag candidate entries `[UNVERIFIED]` and surface the uncertainty rather than dropping them. Never fabricate arXiv IDs, DOIs, or titles from memory. Full protocol in [`shared-references/citation-discipline.md`](../shared-references/citation-discipline.md) § Pre-Search Verification Protocol.

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md` (Policy C — forensic; never silently skip). Use `save_trace.sh` (resolved per the chain in `shared-references/integration-contract.md` §2) or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
