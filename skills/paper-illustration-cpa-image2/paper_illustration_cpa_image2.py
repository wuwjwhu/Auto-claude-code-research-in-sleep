#!/usr/bin/env python3
"""Integration helper for the paper-illustration-cpa-image2 workflow."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


RENDERER = "cpa-image2"
DEFAULT_SIZE = "1536x1024"
DEFAULT_QUALITY = "high"
DEFAULT_TIMEOUT = 180
CPA_PLACEHOLDER_BASE = "http://<CPA_HOST>:<CPA_PORT>"
CPA_PLACEHOLDER_KEY = "<YOUR_API_KEY>"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_workspace(raw_workspace: str | None) -> Path:
    workspace = Path(raw_workspace).expanduser() if raw_workspace else Path.cwd()
    return workspace.resolve()


def output_dir(workspace: Path) -> Path:
    return (workspace / "figures" / "ai_generated").resolve()


def ensure_png_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing PNG file: {path}")
    if not path.read_bytes().startswith(PNG_SIGNATURE):
        raise ValueError(f"expected a PNG file: {path}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def emit_json(payload: dict, *, json_out: Path | None = None) -> int:
    if json_out is not None:
        write_json(json_out, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok", False) else 1


def build_latex_include(caption: str, label: str) -> str:
    return "\n".join(
        [
            r"\begin{figure*}[t]",
            r"    \centering",
            r"    \includegraphics[width=0.95\textwidth]{figures/ai_generated/figure_final.png}",
            f"    \\caption{{{caption}}}",
            f"    \\label{{{label}}}",
            r"\end{figure*}",
            "",
        ]
    )


def cpa_wrapper_path(workspace: Path) -> Path:
    return (Path(__file__).resolve().parent / "cpa_image_api.py").resolve()


def load_cpa_module(workspace: Path) -> ModuleType:
    wrapper = cpa_wrapper_path(workspace)
    if not wrapper.is_file():
        raise FileNotFoundError(f"CPA wrapper not found: {wrapper}")

    spec = importlib.util.spec_from_file_location("aris_cpa_image_api", wrapper)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load CPA wrapper spec: {wrapper}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def env_is_present(name: str, placeholder: str) -> bool:
    value = os.environ.get(name, "").strip()
    return bool(value) and value != placeholder


def run_preflight(workspace: Path, *, json_out: Path | None = None) -> int:
    figures_dir = output_dir(workspace)
    figures_dir.mkdir(parents=True, exist_ok=True)
    wrapper = cpa_wrapper_path(workspace)
    errors: list[str] = []

    if not env_is_present("CPA_API_BASE", CPA_PLACEHOLDER_BASE):
        errors.append("CPA_API_BASE is not set or still uses the placeholder default")
    if not env_is_present("CPA_API_KEY", CPA_PLACEHOLDER_KEY):
        errors.append("CPA_API_KEY is not set or still uses the placeholder default")
    if not wrapper.is_file():
        errors.append(f"missing CPA wrapper: {wrapper}")

    import_ok = False
    if wrapper.is_file():
        try:
            module = load_cpa_module(workspace)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"failed to import CPA wrapper: {exc}")
        else:
            import_ok = all(hasattr(module, attr) for attr in ("generate", "ImageGenConfig"))
            if not import_ok:
                errors.append("CPA wrapper does not expose generate and ImageGenConfig")

    payload = {
        "ok": not errors,
        "renderer": RENDERER,
        "workspace": str(workspace),
        "outputDir": str(figures_dir),
        "cpaWrapper": str(wrapper),
        "cpaApiBasePresent": env_is_present("CPA_API_BASE", CPA_PLACEHOLDER_BASE),
        "cpaApiKeyPresent": env_is_present("CPA_API_KEY", CPA_PLACEHOLDER_KEY),
        "importOk": import_ok,
        "checkedAt": utc_now(),
        "errors": errors,
    }
    return emit_json(payload, json_out=json_out)


def read_prompt(args: argparse.Namespace) -> str:
    sources = [bool(args.prompt), bool(args.prompt_file), bool(args.prompt_stdin)]
    if sum(sources) != 1:
        raise ValueError("provide exactly one of --prompt, --prompt-file, or --prompt-stdin")

    if args.prompt:
        return args.prompt
    if args.prompt_file:
        return Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
    return sys.stdin.read()


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def run_render(
    workspace: Path,
    *,
    prompt: str,
    iteration: int,
    size: str,
    quality: str,
    model: str,
    timeout: int,
    json_out: Path | None = None,
) -> int:
    figures_dir = output_dir(workspace)
    figures_dir.mkdir(parents=True, exist_ok=True)
    target = figures_dir / f"figure_v{iteration}.png"
    receipt = json_out or figures_dir / f"render_v{iteration}.json"

    try:
        module = load_cpa_module(workspace)
        config = module.ImageGenConfig(
            model=model,
            size=size,
            quality=quality,
            n=1,
            format="png",
            output_compression=100,
            response_format="b64_json",
            timeout=timeout,
            outdir=str(figures_dir),
            filename_prefix=f"cpa_image2_v{iteration}",
        )
        images = module.generate(prompt, config)
        if not images:
            raise RuntimeError("CPA Image API returned no images")
        saved_path = Path(images[0].saved_path).expanduser().resolve()
        ensure_png_file(saved_path)
        if saved_path != target:
            shutil.copy2(saved_path, target)
        ensure_png_file(target)
        payload: dict[str, Any] = {
            "ok": True,
            "renderer": RENDERER,
            "workspace": str(workspace),
            "image": str(target),
            "sourceImage": str(saved_path),
            "iteration": iteration,
            "model": model,
            "size": size,
            "quality": quality,
            "format": "png",
            "promptHash": prompt_hash(prompt),
            "revisedPrompt": getattr(images[0], "revised_prompt", None),
            "fileSize": target.stat().st_size,
            "renderedAt": utc_now(),
        }
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "renderer": RENDERER,
            "workspace": str(workspace),
            "image": str(target),
            "iteration": iteration,
            "model": model,
            "size": size,
            "quality": quality,
            "promptHash": prompt_hash(prompt),
            "error": str(exc),
            "renderedAt": utc_now(),
        }

    return emit_json(payload, json_out=receipt)


def run_finalize(
    workspace: Path,
    *,
    best_image: Path,
    caption: str,
    label: str,
    score: float | None,
    review_summary: str | None,
    json_out: Path | None = None,
) -> int:
    figures_dir = output_dir(workspace)
    figures_dir.mkdir(parents=True, exist_ok=True)
    best_image = best_image.expanduser().resolve()
    ensure_png_file(best_image)

    final_image = figures_dir / "figure_final.png"
    latex_include = figures_dir / "latex_include.tex"
    review_log = figures_dir / "review_log.json"

    shutil.copy2(best_image, final_image)
    latex_include.write_text(build_latex_include(caption, label), encoding="utf-8")

    review_payload = {
        "ok": True,
        "renderer": RENDERER,
        "finalizedAt": utc_now(),
        "workspace": str(workspace),
        "bestImage": str(best_image),
        "finalImage": str(final_image),
        "score": score,
        "reviewSummary": review_summary,
        "caption": caption,
        "label": label,
    }
    write_json(review_log, review_payload)

    payload = {
        "ok": True,
        "renderer": RENDERER,
        "workspace": str(workspace),
        "artifacts": {
            "figureFinal": str(final_image),
            "latexInclude": str(latex_include),
            "reviewLog": str(review_log),
        },
        "score": score,
        "reviewSummary": review_summary,
        "finalizedAt": review_payload["finalizedAt"],
    }
    return emit_json(payload, json_out=json_out)


def run_verify(workspace: Path, *, json_out: Path | None = None) -> int:
    figures_dir = output_dir(workspace)
    final_image = figures_dir / "figure_final.png"
    latex_include = figures_dir / "latex_include.tex"
    review_log = figures_dir / "review_log.json"
    render_receipts = sorted(figures_dir.glob("render_v*.json"))

    errors: list[str] = []
    artifacts = {
        "figureFinal": {"path": str(final_image), "exists": final_image.is_file()},
        "latexInclude": {"path": str(latex_include), "exists": latex_include.is_file()},
        "reviewLog": {"path": str(review_log), "exists": review_log.is_file()},
        "renderReceipts": [str(path) for path in render_receipts],
    }

    if final_image.is_file():
        try:
            ensure_png_file(final_image)
        except (FileNotFoundError, ValueError) as exc:
            errors.append(str(exc))
    else:
        errors.append(f"missing artifact: {final_image}")

    if latex_include.is_file():
        latex_text = latex_include.read_text(encoding="utf-8")
        if "figure_final.png" not in latex_text:
            errors.append("latex_include.tex does not reference figures/ai_generated/figure_final.png")
    else:
        errors.append(f"missing artifact: {latex_include}")

    if review_log.is_file():
        try:
            review_payload = json.loads(review_log.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"review_log.json is not valid JSON: {exc}")
        else:
            if str(review_payload.get("finalImage")) != str(final_image):
                errors.append("review_log.json does not point at figure_final.png")
            if review_payload.get("renderer") not in (None, RENDERER):
                errors.append(f"review_log.json does not declare renderer={RENDERER}")
    else:
        errors.append(f"missing artifact: {review_log}")

    for receipt in render_receipts:
        try:
            receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{receipt.name} is not valid JSON: {exc}")
            continue
        if receipt_payload.get("renderer") != RENDERER:
            errors.append(f"{receipt.name} does not declare renderer={RENDERER}")

    payload = {
        "ok": not errors,
        "renderer": RENDERER,
        "workspace": str(workspace),
        "checkedAt": utc_now(),
        "artifacts": artifacts,
        "errors": errors,
    }
    return emit_json(payload, json_out=json_out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Check CPA image generation prerequisites")
    preflight.add_argument("--workspace", help="Paper or project workspace root")
    preflight.add_argument("--json-out", help="Optional path to save the JSON result")

    render = subparsers.add_parser("render", help="Render one CPA image iteration")
    render.add_argument("--workspace", help="Paper or project workspace root")
    render.add_argument("--prompt", help="Final image prompt")
    render.add_argument("--prompt-file", help="Read final image prompt from a UTF-8 file")
    render.add_argument("--prompt-stdin", action="store_true", help="Read final image prompt from stdin")
    render.add_argument("--iteration", type=int, required=True, help="Iteration number for figure_vN.png")
    render.add_argument("--size", default=DEFAULT_SIZE, help=f"Image size, default {DEFAULT_SIZE}")
    render.add_argument("--quality", default=DEFAULT_QUALITY, choices=["low", "medium", "high"])
    render.add_argument("--model", default="gpt-image-2", help="CPA image model name")
    render.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    render.add_argument("--json-out", help="Optional path to save the JSON result")

    finalize = subparsers.add_parser("finalize", help="Finalize the accepted figure artifacts")
    finalize.add_argument("--workspace", help="Paper or project workspace root")
    finalize.add_argument("--best-image", required=True, help="Accepted PNG to promote to figure_final.png")
    finalize.add_argument("--caption", default="[Replace with a paper-ready caption].", help="Caption text to place in latex_include.tex")
    finalize.add_argument("--label", default="fig:replace-me", help="LaTeX figure label")
    finalize.add_argument("--score", type=float, help="Final review score")
    finalize.add_argument("--review-summary", help="Short review summary for review_log.json")
    finalize.add_argument("--json-out", help="Optional path to save the JSON result")

    verify = subparsers.add_parser("verify", help="Verify that final artifacts were emitted correctly")
    verify.add_argument("--workspace", help="Paper or project workspace root")
    verify.add_argument("--json-out", help="Optional path to save the JSON result")

    return parser


def resolve_json_out(raw_json_out: str | None) -> Path | None:
    return Path(raw_json_out).expanduser().resolve() if raw_json_out else None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    workspace = resolve_workspace(getattr(args, "workspace", None))
    json_out = resolve_json_out(getattr(args, "json_out", None))

    if args.command == "preflight":
        return run_preflight(workspace, json_out=json_out)

    if args.command == "render":
        try:
            prompt = read_prompt(args)
        except Exception as exc:  # noqa: BLE001
            return emit_json({"ok": False, "renderer": RENDERER, "error": str(exc)}, json_out=json_out)
        if args.iteration < 1:
            return emit_json({"ok": False, "renderer": RENDERER, "error": "--iteration must be >= 1"}, json_out=json_out)
        return run_render(
            workspace,
            prompt=prompt,
            iteration=args.iteration,
            size=args.size,
            quality=args.quality,
            model=args.model,
            timeout=args.timeout,
            json_out=json_out,
        )

    if args.command == "finalize":
        return run_finalize(
            workspace,
            best_image=Path(args.best_image),
            caption=args.caption,
            label=args.label,
            score=args.score,
            review_summary=args.review_summary,
            json_out=json_out,
        )

    if args.command == "verify":
        return run_verify(workspace, json_out=json_out)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
