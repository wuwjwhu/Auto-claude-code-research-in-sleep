---
name: research-review
description: Get a deep critical review of research from GPT via `codex exec`. Use when user says "review my research", "help me review", "get external review", or wants critical feedback on research ideas, papers, or experimental results.
argument-hint: [topic-or-scope]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, Agent
---

# Research Review via `codex exec` (xhigh reasoning)

Get a multi-round critical review of research work from an external LLM with maximum reasoning depth.

## Constants

- REVIEWER_MODEL = `gpt-5.4` — Model used via `codex exec`. Must be an OpenAI model (e.g., `gpt-5.4`, `o3`, `gpt-4o`)
- **REVIEWER_BACKEND = `codex`** — Default: `codex exec` (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.

## Context: $ARGUMENTS

## Prerequisites

- **Codex CLI** configured in Claude Code:
  ```bash
  codex login
  ```
- This gives you access to the Codex CLI for `codex exec` runs

## Workflow

### Step 1: Gather Research Context
Before calling the external reviewer, compile a comprehensive briefing:
1. Read project narrative documents (e.g., STORY.md, README.md, paper drafts)
2. Read `papers/index.md` when available so proposal-stage review starts from the local prior-work map rather than rebuilding it ad hoc
3. Read any memory/notes files for key findings and experiment history
4. Identify: core claims, methodology, key results, known weaknesses

### Step 2: Initial Review (Round 1)
Send a detailed prompt with xhigh reasoning.

For **proposal-shortlist review** (before experiment planning), ask the reviewer to focus on:
1. Whether the proposal is mathematically / conceptually novel enough
2. Whether the mechanism is technically deep rather than superficial
3. Whether the proposal is clearly differentiated from the closest prior work
4. What the strongest reviewer objection would be
5. What evidence would later be needed to defend the proposal

When `papers/index.md` exists, use it to identify the 2-5 most important comparator papers first. If a comparator paper needs direct inspection, pass file paths to the primary artifacts and prefer `main_tex_path` over `pdf_path` whenever readable TeX exists.

Example framing:

```bash
codex exec "$(cat <<'PROMPT'
[Full research context + specific questions]
Please act as a senior ML reviewer (NeurIPS/ICML level). For this proposal, identify:
1. Logical gaps or unjustified claims
2. Whether the technical mechanism is deep enough to matter
3. Whether the novelty story is legible relative to the closest work
4. The strongest reviewer objection
5. The minimum evidence that would eventually be needed to defend the claim
Please be brutally honest.
PROMPT
)" --skip-git-repo-check 2>&1
```

For **post-results review** (after experiments exist), you can still ask for missing experiments, narrative weaknesses, and contribution sufficiency.

### Step 3: Iterative Dialogue (Rounds 2-N)
For follow-up rounds, run `codex exec` again and include the previous review plus your updates in the prompt.

For each round:
1. **Respond** to criticisms with evidence/counterarguments
2. **Ask targeted follow-ups** on the most actionable points
3. **Request specific deliverables** appropriate to the stage:
   - pre-plan stage: tighter novelty positioning, mechanism clarifications, sharper objections, claim boundaries
   - post-plan stage: experiment designs, paper outlines, claims matrices

Key follow-up patterns:
- "If we reframe X as Y, does that change your assessment?"
- "What's the strongest reason a reviewer would still reject this?"
- "Which part of the mechanism still feels shallow or underspecified?"
- "What is the minimum evidence this proposal would eventually need?"
- "Please write a mock NeurIPS/ICML review with scores"
- "Give me a results-to-claims matrix for possible experimental outcomes"

### Step 4: Convergence
Stop iterating when one of these is true:
- For proposal-stage review: the novelty story, technical mechanism, and reviewer-risk profile are clear enough for the user to compare proposals
- For experiment-stage review: both sides agree on the core claims and their evidence requirements, a concrete experiment plan is established, or the narrative structure is settled

### Step 5: Document Everything
Save the full interaction and conclusions to a review document in the project root:
- Round-by-round summary of criticisms and responses
- Final consensus on claims, narrative, and experiments or evidence requirements
- Claims matrix if discussed
- Prioritized TODO list
- Paper outline if discussed

Update project memory/notes with key review conclusions.

## Key Rules

- ALWAYS run reviews with xhigh reasoning
- Send comprehensive context in Round 1 unless you explicitly want the model to inspect the repo itself
- For prior-work-sensitive proposal review, use `papers/index.md` to route the reviewer toward the strongest comparator papers, and pass file paths to those primary artifacts rather than relying on executor-written prior-work summaries
- Be honest about weaknesses — hiding them leads to worse feedback
- Push back on criticisms you disagree with, but accept valid ones
- Focus on ACTIONABLE feedback
- At proposal-shortlist stage, prioritize conceptual sharpness, technical depth, and novelty positioning before detailed experiment-package design
- Save the raw review output you want to reuse in later rounds
- The review document should be self-contained (readable without the conversation)

## Prompt Templates

### For initial proposal review:
"I'm going to present a research proposal for your critical review. Please act as a senior ML reviewer (NeurIPS/ICML level) and focus on novelty, mechanism quality, and likely reviewer objections."

### For experiment design:
"Please design the minimal additional experiment package that gives the highest acceptance lift per GPU week. Our compute: [describe]. Be very specific about configurations."

### For paper structure:
"Please turn this into a concrete paper outline with section-by-section claims and figure plan."

### For claims matrix:
"Please give me a results-to-claims matrix: what claim is allowed under each possible outcome of experiments X and Y?"

### For mock review:
"Please write a mock NeurIPS review with: Summary, Strengths, Weaknesses, Questions for Authors, Score, Confidence, and What Would Move Toward Accept."

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
