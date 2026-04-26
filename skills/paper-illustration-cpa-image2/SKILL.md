---
name: paper-illustration-cpa-image2
description: "Generate publication-quality academic illustrations through a CPA Image API service using the same Claude planning, layout, style, review, and refinement workflow as paper-illustration-image2, but without Codex desktop/app-server."
argument-hint: [description-or-method-file]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, WebSearch
---

# Paper Illustration CPA Image2

Generate publication-quality paper figures using **Claude as the planner/reviewer**
and a **CPA Image API service** as the raster renderer.

## Core Design Philosophy

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                    MULTI-STAGE ITERATIVE WORKFLOW                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   User Request                                                           │
│       │                                                                  │
│       ▼                                                                  │
│   ┌─────────────┐                                                        │
│   │   Claude    │ ◄─── Step 1: Parse request, create initial prompt     │
│   │  (Planner)  │      - Extract components, labels, and data flow       │
│   │             │      - Write a paper-ready figure brief                │
│   └──────┬──────┘                                                        │
│          │                                                               │
│          ▼                                                               │
│   ┌─────────────┐                                                        │
│   │   Claude    │ ◄─── Step 2: Optimize layout description               │
│   │   Layout    │      - Refine component positioning                    │
│   │   Review    │      - Optimize spacing and grouping                   │
│   └──────┬──────┘                                                        │
│          │                                                               │
│          ▼                                                               │
│   ┌─────────────┐                                                        │
│   │   Claude    │ ◄─── Step 3: CVPR/NeurIPS style verification           │
│   │   Style     │      - Check palette, arrows, and label standards      │
│   │   Check     │      - Tighten the prompt before rendering             │
│   └──────┬──────┘                                                        │
│          │                                                               │
│          ▼                                                               │
│   ┌─────────────┐                                                        │
│   │ cpa-image2  │ ◄─── Step 4: CPA Image API generation                  │
│   │   helper    │      - Call ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py     │
│   │ + CPA API   │      - Save exact figure_vN.png artifacts              │
│   └──────┬──────┘                                                        │
│          │                                                               │
│          ▼                                                               │
│   ┌─────────────┐                                                        │
│   │   Claude    │ ◄─── Step 5: STRICT visual review + SCORE (1-10)      │
│   │  (Reviewer) │      - Verify logic, labels, arrows, and aesthetics    │
│   │   STRICT!   │      - Reject unclear or non-paper-ready figures       │
│   └──────┬──────┘                                                        │
│          │                                                               │
│          ▼                                                               │
│   Score ≥ 9? ──YES──► Accept & Output                                    │
│          │                                                               │
│          NO                                                              │
│          │                                                               │
│          ▼                                                               │
│   Generate SPECIFIC improvement feedback ──► Loop back to Step 2        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Constants

- **RENDERER = `cpa-image2`** — CPA Image API generation endpoint through `cpa-image-generation/cpa_image_api.py`
- **MAX_ITERATIONS = 5** — Maximum refinement rounds
- **TARGET_SCORE = 9** — Minimum acceptable score (1-10)
- **OUTPUT_DIR = `figures/ai_generated/`** — Output directory
- **TEXT_LANGUAGE = `English`** — Default figure text language unless the user requests otherwise
- **DEFAULT_SIZE = `1536x1024`** — Default paper-friendly image size
- **DEFAULT_QUALITY = `high`** — Default CPA quality setting
- **CANONICAL_HELPER = `python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py`** — Preflight, render, finalize, verify, and repair path for this integration

## CVPR/ICLR/NeurIPS Top-Tier Conference Style Guide

**What "CVPR Style" Actually Means:**

### Visual Standards
- **Clean white background** — No decorative patterns or gradients unless extremely subtle
- **Sans-serif fonts** — Arial, Helvetica, or similarly clean paper-friendly typography
- **Subtle color palette** — Use 3-5 coordinated colors, not rainbow colors
- **Print-friendly** — Must remain understandable in grayscale
- **Professional borders** — Thin to medium, clean, and consistent

### Layout Standards
- **Horizontal flow** — Left-to-right is the default for pipelines
- **Clear grouping** — Use spacing or subtle grouping boxes for related modules
- **Consistent sizing** — Similar components should have similar sizes
- **Balanced whitespace** — Avoid both cramped and overly sparse layouts

### Arrow Standards (MOST CRITICAL)
- **Thick strokes** — Arrows must remain visible after paper scaling
- **Clear arrowheads** — Large, unmistakable arrowheads
- **Dark colors** — Prefer black or dark gray arrows
- **Labeled** — Important arrows should show what flows through them
- **No crossings** — Reorganize the figure to avoid crossings where possible
- **CORRECT DIRECTION** — Arrows must point to the right target

### Visual Appeal (Academic Professional Style)

**Goal: Neither too conservative nor too flashy, find the right balance**

#### Should have
- **Subtle gradients** — Gentle same-family gradients are acceptable
- **Rounded corners** — Modern but restrained rounded blocks
- **Clear hierarchy** — Main modules larger, secondary modules smaller
- **Consistent color coding** — Stable mapping between module types and colors
- **Professional typography** — Clean labels with readable size hierarchy

#### Avoid
- Rainbow gradients
- Heavy drop shadows
- 3D perspective effects
- Glowing effects
- Decorative clip-art icons
- Slide-deck styling that feels flashy rather than paper-ready

#### Ideal effect
- Looks intentional, professional, and immediately readable
- Has moderate visual appeal without becoming decorative
- Feels appropriate for a top-tier conference paper figure
- Survives PDF scaling and grayscale printing

### What to AVOID (CRITICAL)
- Thin, hairline arrows
- Unlabeled or ambiguous connections
- Tiny unreadable text
- Flat, boring box soup with no hierarchy
- Over-decorated figures with shadows/glows/icons
- Wrong arrow directions

## Scope

| Figure Type | Quality | Examples |
|-------------|---------|----------|
| **Architecture diagrams** | Excellent | Model architecture, pipeline, encoder-decoder |
| **Method illustrations** | Excellent | Conceptual diagrams, algorithm flowcharts |
| **Conceptual figures** | Good | Comparison diagrams, taxonomy trees |

**Not for:** Statistical plots (use `/paper-figure`), deterministic vector topology figures (prefer `/figure-spec`), photo-realistic scenes

## Workflow: MUST EXECUTE ALL STEPS

### Step 0: Pre-flight Check

Render this checklist explicitly before starting:

```text
paper-illustration-cpa-image2 integration checklist:
   [ ] 1. python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py preflight --workspace <cwd> --json-out figures/ai_generated/preflight_cpa.json
   [ ] 2. Confirm preflight JSON says ok=true before rendering
   [ ] 3. Render via python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py render --workspace <cwd> --iteration N --prompt-file <prompt_file>
   [ ] 4. Review the generated figure visually and score it
   [ ] 5. Finalize via python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py finalize --workspace <cwd> --best-image <best_png>
   [ ] 6. Verify artifacts via python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py verify --workspace <cwd> --json-out figures/ai_generated/verify_cpa.json
```

1. Create `figures/ai_generated/` if it does not exist.
2. Confirm the request is suitable for a raster illustration:
   - architecture diagram
   - conceptual method figure
   - workflow illustration
3. Prefer **English figure text** unless the user asked otherwise.
4. Confirm CPA prerequisites are available:
   - `CPA_API_BASE`
   - `CPA_API_KEY`
   - `cpa-image-generation/cpa_image_api.py`
5. Run:

```bash
python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py preflight \
  --workspace <cwd> \
  --json-out figures/ai_generated/preflight_cpa.json
```

6. If preflight is not `ok=true`, stop and say so clearly. Do not restart CPA containers or alter CPA service state.

## Step 1: Claude Plans the Figure

Turn the user request into a **fully specified image prompt**. Include:

- figure type
- exact modules / stages
- flow direction
- labels to show
- data-flow arrows
- style constraints
- what to avoid

When the input is a method note or a paper section, summarize it first into a
clean figure brief before writing the final image prompt.

## Step 2: Layout Optimization

This step is required. Before rendering, refine the prompt into a concrete
layout plan:

- exact module order
- spacing and grouping
- relative module prominence
- arrow routing and likely collision points

Check for:

- missing components
- confusing layout
- weak flow hierarchy
- likely arrow-direction ambiguity or clutter

## Step 3: Style Verification

This step is also required. Check the prompt against the intended paper style
before rendering:

- palette is restrained and academic
- arrows are thick, dark, and readable
- labels are concise and in English unless requested otherwise
- the figure will read clearly in grayscale / print
- no glow, rainbow gradient, or slide-deck decoration slips in

## Step 4: Generate Through CPA Image API

Use the helper render command. Prefer `--prompt-file` for long prompts:

```bash
python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py render \
  --workspace <cwd> \
  --iteration 1 \
  --size 1536x1024 \
  --quality high \
  --prompt-file figures/ai_generated/prompt_v1.txt \
  --json-out figures/ai_generated/render_v1.json
```

The helper calls the CPA Image API generation endpoint through
`cpa-image-generation/cpa_image_api.py`. It does **not** use the CPA Responses API.

If generation fails, report the CPA/helper error directly instead of hiding it.

## Step 5: Review the Output

Review the generated image with a strict checklist:

- are all major components present?
- is the logical flow obvious?
- are labels readable?
- do arrows point the right way?
- does the figure look paper-ready rather than like a slide?

Score it from 1-10.

## Step 6: Refine if Needed

If score < 9, write a targeted refinement prompt:

- say exactly what was wrong
- say what to preserve
- regenerate to `figure_v2.png`, `figure_v3.png`, etc.

Keep refinement feedback concrete:

- `Increase spacing between genome scan and scoring modules`
- `Make the off-target branch thinner and secondary`
- `Use cleaner English labels: "Candidate sgRNA library", not "sgRNA library 23 bp"`

For each iteration, save a new prompt file such as `figures/ai_generated/prompt_v2.txt` and render with the matching `--iteration` value.

## Step 7: Finalize And Verify

When accepted:

- run the canonical helper to promote the best image to `figure_final.png`
- let the helper write `latex_include.tex`
- let the helper write `review_log.json`
- run helper verification before claiming success

```bash
python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py finalize \
  --workspace <cwd> \
  --best-image figures/ai_generated/figure_vN.png \
  --score 9 \
  --review-summary "Accepted after strict review; labels and arrows are paper-ready."

python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py verify \
  --workspace <cwd> \
  --json-out figures/ai_generated/verify_cpa.json
```

Suggested LaTeX:

```latex
\begin{figure*}[t]
    \centering
    \includegraphics[width=0.95\textwidth]{figures/ai_generated/figure_final.png}
    \caption{[Replace with a paper-ready caption].}
    \label{fig:[replace-me]}
\end{figure*}
```

## Key Rules

1. Never skip Step 2 or Step 3; layout and style checks are required.
2. Never skip the final visual review.
3. Never accept a figure that is logically wrong just because it looks attractive.
4. Use the CPA Image API generation endpoint, not Responses API.
5. Surface CPA connectivity, auth, or generation failures honestly.
6. Do not restart containers or modify CPA service state without explicit user consent.
7. Keep figure text in English unless the user requested another language.
8. Prefer 1-3 strong refinement rounds over many shallow ones.
9. Use specific, actionable refinement feedback instead of vague comments.
10. Review arrow direction, label clarity, and visual hierarchy every round.
11. Accept only figures that look paper-ready, not slide-ready.
12. Always use `~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py finalize` to emit final artifacts.
13. Always use `~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py verify` before claiming success.

## Repair Path

If rendering succeeded but final artifacts were skipped, repair the integration explicitly:

```bash
python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py finalize \
  --workspace <cwd> \
  --best-image figures/ai_generated/figure_vN.png

python3 ~/.claude/skills/paper-illustration-cpa-image2/paper_illustration_cpa_image2.py verify \
  --workspace <cwd> \
  --json-out figures/ai_generated/verify_cpa.json
```

If preflight fails, fix CPA environment/connectivity outside this skill, then rerun preflight. Do not perform container restarts from this workflow.
