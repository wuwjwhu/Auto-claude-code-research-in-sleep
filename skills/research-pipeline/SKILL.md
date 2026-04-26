---
name: research-pipeline
description: "Full research pipeline: Workflow 1 (idea discovery) → implementation → Workflow 2 (auto review loop) → Workflow 3 (paper writing, optional). Goes from a broad research direction all the way to a polished PDF. Use when user says \"全流程\", \"full pipeline\", \"从找idea到投稿\", \"end-to-end research\", or wants the complete autonomous research lifecycle."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill
---

# Full Research Pipeline: Idea → Experiments → Submission

End-to-end autonomous research workflow for: **$ARGUMENTS**

## Constants

- **AUTO_PROCEED = false** — When `false` (default), always waits for explicit user confirmation before proceeding past Stage 1. Do not auto-select the final proposal. If the user explicitly overrides this, only auto-continue after the shortlist has been presented clearly.
- **ARXIV_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during literature survey. When `false` (default), only fetches metadata via arXiv API. Passed through to `/idea-discovery` → `/research-lit`.
- **HUMAN_CHECKPOINT = false** — When `true`, the auto-review loops (Stage 4) pause after each round's review to let you see the score and provide custom modification instructions before fixes are implemented. When `false` (default), loops run fully autonomously. Passed through to `/auto-review-loop`.
- **REVIEWER_DIFFICULTY = medium** — How adversarial the reviewer is. `medium` (default): standard `codex exec` review. `hard`: adds reviewer memory + debate protocol. `nightmare`: GPT reads repo directly via `codex exec` + memory + debate. Passed through to `/auto-review-loop`.
- **AUTO_WRITE = false** — When `true`, automatically invoke Workflow 3 (`/paper-writing`) after Stage 5. Requires `VENUE` to be set. When `false` (default), Stage 5 generates `NARRATIVE_REPORT.md` and stops — user invokes `/paper-writing` manually.
- **VENUE = ICLR** — Target venue for paper writing (Stage 6). Only used when `AUTO_WRITE=true`. Options: `ICLR`, `NeurIPS`, `ICML`, `CVPR`, `ACL`, `AAAI`, `ACM`, `IEEE_CONF`, `IEEE_JOURNAL`.

> 💡 Override via argument, e.g., `/research-pipeline "topic" — AUTO_PROCEED: false, human checkpoint: true, difficulty: nightmare, auto_write: true, venue: NeurIPS`.

## Overview

This skill chains the entire research lifecycle into a single pipeline:

```
/idea-discovery → implement → /run-experiment → /auto-review-loop → /paper-writing (optional)
├── Workflow 1 ──┤            ├────────── Workflow 2 ──────────────┤ ├── Workflow 3 ──┤
```

It orchestrates up to three major workflows plus the implementation bridge between them. Workflow 3 (paper writing) is optional and controlled by `AUTO_WRITE`.

## Pipeline

### Stage 1: Idea Discovery (Workflow 1)

If `RESEARCH_BRIEF.md` exists in the project root, it will be automatically loaded as detailed context (replaces one-line prompt). See `templates/RESEARCH_BRIEF_TEMPLATE.md`.

Invoke the idea discovery pipeline:

```
/idea-discovery "$ARGUMENTS"
```

This internally runs: `/research-lit` → `/idea-creator` → `/novelty-check` → `/research-review` → user choice → `/research-refine` → `/experiment-plan`

**Output:** `idea-stage/IDEA_REPORT.md` with a ranked shortlist of hardened proposals, then `refine-logs/FINAL_PROPOSAL.md` and `refine-logs/EXPERIMENT_PLAN.md` for the chosen proposal.

**🚦 Gate 1 — Human Checkpoint:**

After the shortlist is hardened and presented, **pause and present the top proposals to the user**:

```
📋 Idea Discovery complete. Top proposals:

1. [Proposal 1 title] — Novelty: [summary], Technical depth: [summary]
2. [Proposal 2 title] — Novelty: [summary], Technical depth: [summary]
3. [Proposal 3 title] — Novelty: [summary], Technical depth: [summary]

Which proposal should I carry forward into the final refined proposal and experiment plan?
```

**Default behavior:** wait for explicit user choice before continuing. The user may:
- **Approve a proposal** → proceed to Stage 2.
- **Pick a different proposal** → proceed with their choice.
- **Request changes** (e.g., "focus more on X", "make the shortlist more theoretical") → update the idea prompt with user feedback, re-run `/idea-discovery` with refined constraints, and present again.
- **Reject all proposals** → collect feedback on what's missing, re-run Stage 1 with adjusted research direction. Repeat until the user commits to a proposal.
- **Stop here** → save current state to `idea-stage/IDEA_REPORT.md` for future reference.

If the user explicitly enables auto-proceed, only continue after clearly presenting the shortlist and chosen proposal. Do not silently auto-pick based on pilot signal because Workflow 1 is no longer pilot-first.

### Stage 2: Implementation

Once the user confirms which proposal to pursue:

1. **Read the chosen proposal details** from `refine-logs/FINAL_PROPOSAL.md` and the validation context from `idea-stage/IDEA_REPORT.md`

2. **Implement the full experiment program**:
   - Implement the refined method described in `FINAL_PROPOSAL.md`
   - Use `EXPERIMENT_PLAN.md` as the claim-driven validation roadmap
   - Add proper evaluation metrics and logging (wandb if configured)
   - Write clean, reproducible experiment scripts
   - Follow existing codebase conventions

3. **Code review**: Before deploying, do a self-review:
   - Are all hyperparameters configurable via argparse?
   - Is the random seed fixed and controllable?
   - Are results saved to JSON/CSV for later analysis?
   - Is there proper logging for debugging?

### Stage 3: Deploy Experiments (Workflow 2 — Part 1)

Deploy the full-scale experiments. **Route by job count**:

**Small batch (≤5 jobs)** — direct deployment:
```
/run-experiment [experiment command]
```

**Large batch (≥10 jobs, multi-seed sweeps, teacher→student chains)** — use the queue scheduler:
```
/experiment-queue [grid spec or manifest]
```

`experiment-bridge` (Workflow 1.5) auto-routes based on milestone job count. For pipeline runs with multi-seed sweeps from the start, you can override globally with `--- batch: queue` to force `/experiment-queue` for all milestones.

**What this does:**
- Check GPU availability on configured servers
- Sync code to remote server
- Launch experiments in screen sessions with proper CUDA_VISIBLE_DEVICES
- For `/experiment-queue`: also OOM retry, stale-screen cleanup, phase dependencies, crash-safe state
- Verify experiments started successfully

**Monitor progress:**

```
/monitor-experiment [server]
```

Wait for experiments to complete. Collect results.

### Stage 4: Auto Review Loop (Workflow 2 — Part 2)

Once initial results are in, start the autonomous improvement loop:

```
/auto-review-loop "$ARGUMENTS — [chosen proposal title], difficulty: $REVIEWER_DIFFICULTY"
```

**What this does (up to 4 rounds):**
1. GPT-5.4 xhigh reviews the work (score, weaknesses, minimum fixes)
2. Claude Code implements fixes (code changes, new experiments, reframing)
3. Deploy fixes, collect new results
4. Re-review → repeat until score ≥ 6/10 or 4 rounds reached

**Output:** `review-stage/AUTO_REVIEW.md` with full review history and final assessment.

### Stage 5: Research Summary & Writing Handoff

After the auto-review loop completes, prepare the handoff for paper writing.

**Step 1:** Write a final research status report.

**Step 2:** Generate `NARRATIVE_REPORT.md` from:
- `IDEA_REPORT.md` (shortlist, novelty justification, why the chosen proposal won)
- `FINAL_PROPOSAL.md` (the chosen/refined method)
- Implementation details from the repo
- Experiment configs and final results
- `AUTO_REVIEW.md` (review history, weaknesses fixed, remaining limitations)

The narrative report must contain:
- Problem statement and core claim
- Method summary
- Key quantitative results with evidence for each claim
- Figure/table inventory (which exist, which need manual creation)
- Limitations and remaining follow-up items

**Output:** `NARRATIVE_REPORT.md` + research pipeline report.

```markdown
# Research Pipeline Report

**Direction**: $ARGUMENTS
**Chosen Proposal**: [title]
**Date**: [start] → [end]
**Pipeline**: idea-discovery → implement → run-experiment → auto-review-loop

## Journey Summary
- Proposals generated: X → filtered to Y → shortlisted Z → chose 1
- Implementation: [brief description of what was built]
- Experiments: [number of GPU experiments, total compute time]
- Review rounds: N/4, final score: X/10

## Writing Handoff
- NARRATIVE_REPORT.md: ✅ generated
- Venue: [VENUE or "not set — run /paper-writing manually"]
- Manual figures needed: [list or "none"]

## Remaining TODOs (if any)
- [items flagged by reviewer that weren't addressed]
```

### Stage 6: Paper Writing (Workflow 3 — Optional)

**Skip this stage if `AUTO_WRITE=false` (default).** Present the `/paper-writing` command for manual use:

```
📝 Research complete. To write the paper:
/paper-writing "NARRATIVE_REPORT.md" — venue: ICLR
```

**If `AUTO_WRITE=true`:**

🚦 **Gate 2 — Writing Checkpoint:**

```
📝 Research pipeline complete. Ready for Workflow 3.

- Venue: [VENUE]
- Input: NARRATIVE_REPORT.md
- Manual figures required: [list or none]
- Next step: /paper-writing "NARRATIVE_REPORT.md — venue: [VENUE]"

Proceeding with paper writing...
```

Checks before proceeding:
- If `VENUE` is missing → stop and ask. Do NOT silently use a default venue.
- If manual figures are required → pause and list them. Wait for user to add them.

Then invoke:

```
/paper-writing "NARRATIVE_REPORT.md" — venue: $VENUE
```

This delegates to Workflow 3 which handles its own phases:
`/paper-plan → /paper-figure → /paper-write → /paper-compile → /auto-paper-improvement-loop`

When Workflow 3 finishes, update the pipeline report with:
- Paper writing completion status
- Final PDF path (`paper/main.pdf`)
- Improvement scores (round 0 → round N)
- Remaining issues

**Output:** `paper/` directory with LaTeX source, compiled PDF, and `PAPER_IMPROVEMENT_LOG.md`.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- **Human checkpoint after Stage 1 is user-choice gated.** Do not proceed without a chosen proposal unless the user explicitly requests autonomous continuation.
- **Stages 2-4 can run autonomously** once the user confirms the chosen proposal. This is the "sleep and wake up to results" part.
- **If Stage 4 ends at round 4 without positive assessment**, stop and report remaining issues. Do not loop forever.
- **Budget awareness**: Track total GPU-hours across the pipeline. Flag if approaching user-defined limits.
- **Documentation**: Every stage updates its own output file. The full history should be self-contained.
- **Fail gracefully**: If any stage fails (no good proposals, experiments crash, review loop stuck), report clearly and suggest alternatives rather than forcing forward.

## Typical Timeline

| Stage | Duration | Can sleep? |
|-------|----------|------------|
| 1. Idea Discovery | 30-60 min | Yes if the user approves shortlist-to-proposal flow |
| 2. Implementation | 15-60 min | Yes (autonomous after Gate 1) |
| 3. Deploy | 5 min + experiment time | Yes ✅ |
| 4. Auto Review | 1-4 hours (depends on experiments) | Yes ✅ |

**Sweet spot**: Run Stage 1-2 in the evening, launch Stage 3-4 before bed, wake up to a reviewed paper.
