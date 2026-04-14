#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"


def dedent_prompt(block: str) -> str:
    match = re.search(r"prompt:\s*\|\n([\s\S]*)", block)
    if not match:
        return ""

    lines = match.group(1).splitlines()
    while lines and not lines[-1].strip():
        lines.pop()

    non_empty = [line for line in lines if line.strip()]
    indent = min((len(line) - len(line.lstrip(" ")) for line in non_empty), default=0)
    return "\n".join(line[indent:] if len(line) >= indent else line for line in lines).rstrip()


def replace_mcp_block(match: re.Match[str]) -> str:
    prompt = dedent_prompt(match.group("body"))
    if not prompt:
        return match.group(0)

    return (
        "```bash\n"
        "codex exec \"$(cat <<'PROMPT'\n"
        f"{prompt}\n"
        "PROMPT\n"
        ")\" --skip-git-repo-check 2>&1\n"
        "```"
    )


def migrate_file(path: Path) -> bool:
    text = path.read_text()
    original = text

    for needle in [
        ", mcp__codex__codex, mcp__codex__codex-reply",
        ", mcp__codex__codex-reply, mcp__codex__codex",
        ", mcp__codex__codex",
        ", mcp__codex__codex-reply",
    ]:
        text = text.replace(needle, "")

    text = re.sub(
        r"```(?:yaml|text)?\n(?P<header>mcp__codex__codex(?:-reply)?):\n(?P<body>[\s\S]*?)```",
        replace_mcp_block,
        text,
    )

    replacements = [
        ("Codex MCP Server", "Codex CLI"),
        ("Codex MCP server", "Codex CLI"),
        ("used via Codex MCP", "used via `codex exec`"),
        ("via Codex MCP", "via `codex exec`"),
        ("Codex MCP", "`codex exec`"),
        ("Default: Codex MCP (xhigh).", "Default: `codex exec` (xhigh)."),
        ("standard MCP review", "standard `codex exec` review"),
        ("MCP-based review", "`codex exec`-based review"),
        ("MCP Review + Reviewer Memory", "`codex exec` Review + Reviewer Memory"),
        ("MCP Review", "`codex exec` Review"),
        ("claude mcp add codex -s user -- codex mcp-server", "codex login"),
        (
            "This gives Claude Code access to `mcp__codex__codex` and `mcp__codex__codex-reply` tools",
            "This gives you access to the Codex CLI for `codex exec` runs",
        ),
        (
            "Use `mcp__codex__codex-reply` with the returned `threadId` to continue the conversation:",
            "For follow-up rounds, run `codex exec` again and include the previous review plus your updates in the prompt:",
        ),
        (
            "Use `mcp__codex__codex-reply` with the saved threadId:",
            "For follow-up rounds, run `codex exec` again and include the saved review context:",
        ),
        (
            "Use `mcp__codex__codex-reply` with the saved threadId to maintain conversation context.",
            "For later rounds, re-run `codex exec` with the prior review and your revisions pasted into the prompt.",
        ),
        (
            "If this is round 2+, use `mcp__codex__codex-reply` with the saved threadId to maintain conversation context.",
            "If this is round 2+, re-run `codex exec` with the prior review, your rebuttal, and the latest project state pasted into the prompt.",
        ),
        ("Save the threadId for follow-up.", "Save the full raw review output for follow-up rounds."),
        (
            "Save threadId from first call, use `mcp__codex__codex-reply` for subsequent rounds",
            "Save the raw review output from the first call and paste the relevant excerpts into subsequent `codex exec` prompts",
        ),
        (
            "**CRITICAL: Save the `threadId`** from this call for all later rounds.",
            "**CRITICAL: Save the FULL raw review output** from this call for all later rounds.",
        ),
        ("**Do NOT use MCP.** Instead, let GPT access the repo autonomously via `codex exec`:", "Use `codex exec` so GPT can access the repo autonomously:"),
        ("`mcp__codex__codex-reply`", "`codex exec`"),
        ("`mcp__codex__codex`", "`codex exec`"),
        ("mcp__codex__codex-reply", "codex exec"),
        ("mcp__codex__codex", "codex exec"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    text = text.replace("- ALWAYS use `config: {\"model_reasoning_effort\": \"xhigh\"}` for reviews", "- ALWAYS run reviews with xhigh reasoning")
    text = text.replace("- Document the threadId for potential future resumption", "- Save the raw review output you want to reuse in later rounds")
    text = text.replace(
        "**Checkpoint:** Update `refine-logs/REFINE_STATE.json` with `{"phase": "review", "round": 1, "threadId": "<saved>", "last_score": <parsed>, "last_verdict": "<parsed>", ...}`.",
        "**Checkpoint:** Update `refine-logs/REFINE_STATE.json` with `{"phase": "review", "round": 1, "last_score": <parsed>, "last_verdict": "<parsed>", ...}`.",
    )
    text = text.replace(
        "**Checkpoint:** Update `refine-logs/REFINE_STATE.json` with `{"phase": "review", "round": N, "threadId": "<saved>", "last_score": <parsed>, "last_verdict": "<parsed>", ...}`.",
        "**Checkpoint:** Update `refine-logs/REFINE_STATE.json` with `{"phase": "review", "round": N, "last_score": <parsed>, "last_verdict": "<parsed>", ...}`.",
    )

    if text == original:
        return False

    path.write_text(text)
    return True


def main() -> None:
    changed = []
    for path in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
        if migrate_file(path):
            changed.append(path.relative_to(REPO_ROOT))

    if not changed:
        print("No files changed.")
        return

    for path in changed:
        print(path)
    print(f"\nUpdated {len(changed)} files.")


if __name__ == "__main__":
    main()
