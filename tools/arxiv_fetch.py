#!/usr/bin/env python3
"""CLI helper for searching and downloading arXiv papers.

Used by the ``arxiv`` skill (skills/arxiv/SKILL.md).

Commands
--------
search    Search arXiv and print results as JSON.
download  Download paper artifacts by arXiv ID.

Examples
--------
python3 tools/arxiv_fetch.py search "attention mechanism" --max 10
python3 tools/arxiv_fetch.py search "id:2301.07041" --max 1
python3 tools/arxiv_fetch.py download 2301.07041 --dir papers
python3 tools/arxiv_fetch.py download 2301.07041 --dir papers --artifact pdf
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

_ATOM_NS = "http://www.w3.org/2005/Atom"
_API_BASE = "http://export.arxiv.org/api/query"
_USER_AGENT = (
    "arxiv-skill/1.0 "
    "(github.com/wanshuiyin/Auto-claude-code-research-in-sleep)"
)
_MIN_PDF_BYTES = 10_240
_MIN_SOURCE_BYTES = 1_024
_NEW_STYLE_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_OLD_STYLE_ID_RE = re.compile(r"^[A-Za-z.-]+/\d{7}(v\d+)?$")
_ARTIFACT_CHOICES = ("pdf", "source", "both")


def _normalize_id(arxiv_id: str) -> str:
    """Strip URL/version noise and return a clean arXiv ID."""
    value = arxiv_id.strip()
    if "/abs/" in value:
        value = value.split("/abs/", 1)[1]
    if value.startswith("id:"):
        value = value[3:]
    if "v" in value.split(".")[-1]:
        value = value.rsplit("v", 1)[0]
    return value


def _looks_like_arxiv_id(value: str) -> bool:
    """Return True when the input resembles a modern or legacy arXiv ID."""
    value = value.strip()
    return bool(_NEW_STYLE_ID_RE.match(value) or _OLD_STYLE_ID_RE.match(value))


def _api_url(query: str, max_results: int, start: int) -> str:
    """Build the arXiv API URL for a search query or specific ID lookup."""
    query = query.strip()
    if query.startswith("id:"):
        params = {"id_list": _normalize_id(query)}
    elif _looks_like_arxiv_id(query):
        params = {"id_list": _normalize_id(query)}
    else:
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    return f"{_API_BASE}?{urllib.parse.urlencode(params)}"


def _fetch_atom(url: str) -> ET.Element:
    """Fetch an arXiv Atom feed and return the parsed XML root."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return ET.fromstring(resp.read())


def _parse_entry(entry: ET.Element) -> dict:
    """Extract structured fields from a single Atom <entry> element."""
    raw_id = entry.findtext(f"{{{_ATOM_NS}}}id", "")
    arxiv_id = _normalize_id(raw_id)
    title = (entry.findtext(f"{{{_ATOM_NS}}}title", "") or "").strip().replace("\n", " ")
    abstract = (entry.findtext(f"{{{_ATOM_NS}}}summary", "") or "").strip().replace("\n", " ")
    published = (entry.findtext(f"{{{_ATOM_NS}}}published", "") or "")[:10]
    updated = (entry.findtext(f"{{{_ATOM_NS}}}updated", "") or "")[:10]
    authors = [
        author.findtext(f"{{{_ATOM_NS}}}name", "")
        for author in entry.findall(f"{{{_ATOM_NS}}}author")
    ]
    categories = [
        category.get("term", "")
        for category in entry.findall(f"{{{_ATOM_NS}}}category")
        if category.get("term")
    ]
    return {
        "id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "updated": updated,
        "categories": categories,
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
        "src_url": f"https://arxiv.org/src/{arxiv_id}",
    }


def search(query: str, max_results: int = 10, start: int = 0) -> list[dict]:
    """Search arXiv and return a list of paper dictionaries."""
    url = _api_url(query, max_results=max_results, start=start)
    root = _fetch_atom(url)
    return [_parse_entry(entry) for entry in root.findall(f"{{{_ATOM_NS}}}entry")]


def _download_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt == 1:
                time.sleep(5)
                continue
            raise
    raise RuntimeError(f"Failed to download {url} after retries")


def _artifact_result(path: Path, skipped: bool, size_bytes: int | None = None, **extra: object) -> dict:
    size_kb = (size_bytes if size_bytes is not None else path.stat().st_size) // 1024
    return {
        "path": str(path),
        "size_kb": size_kb,
        "skipped": skipped,
        **extra,
    }


def _download_pdf(clean_id: str, dest_dir: Path, safe_id: str) -> dict:
    dest = dest_dir / f"{safe_id}.pdf"
    if dest.exists():
        return _artifact_result(dest, skipped=True, status="ok")

    data = _download_bytes(f"https://arxiv.org/pdf/{clean_id}.pdf")
    if len(data) < _MIN_PDF_BYTES:
        raise ValueError(
            f"Downloaded file is only {len(data)} bytes - likely an error page, not a PDF"
        )
    dest.write_bytes(data)
    return _artifact_result(dest, skipped=False, size_bytes=len(data), status="ok")


def _safe_extract_tar(archive_path: Path, output_dir: Path) -> tuple[bool, bool, str | None]:
    if output_dir.exists():
        return True, True, None

    temp_dir = Path(tempfile.mkdtemp(prefix=f"{output_dir.name}.", dir=str(output_dir.parent)))
    try:
        root = temp_dir.resolve()
        with tarfile.open(archive_path, mode="r:*") as tar:
            members = tar.getmembers()
            for member in members:
                member_path = (temp_dir / member.name).resolve()
                try:
                    member_path.relative_to(root)
                except ValueError:
                    raise ValueError(f"Unsafe path in archive: {member.name}")
            tar.extractall(temp_dir, members=members, filter="data")
        temp_dir.rename(output_dir)
        return True, False, None
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False, False, str(exc)


def _download_source(clean_id: str, dest_dir: Path, safe_id: str) -> dict:
    archive_path = dest_dir / f"{safe_id}.src.tar.gz"
    extract_dir = dest_dir / f"{safe_id}.src"
    result: dict[str, object] = {
        "archive_path": str(archive_path),
        "extract_dir": str(extract_dir),
    }

    if archive_path.exists():
        result["archive"] = _artifact_result(archive_path, skipped=True, status="ok")
    else:
        try:
            data = _download_bytes(f"https://arxiv.org/src/{clean_id}")
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):
                result["archive"] = {"status": "unavailable", "reason": f"HTTP {exc.code}"}
                result["extract"] = {"status": "skipped", "reason": "source unavailable"}
                return result
            raise

        if len(data) < _MIN_SOURCE_BYTES:
            result["archive"] = {
                "status": "unavailable",
                "reason": f"source archive too small ({len(data)} bytes)",
            }
            result["extract"] = {"status": "skipped", "reason": "source unavailable"}
            return result

        archive_path.write_bytes(data)
        result["archive"] = _artifact_result(archive_path, skipped=False, size_bytes=len(data), status="ok")

    success, skipped, error = _safe_extract_tar(archive_path, extract_dir)
    if success:
        result["extract"] = {
            "status": "ok",
            "path": str(extract_dir),
            "skipped": skipped,
        }
    else:
        result["extract"] = {
            "status": "failed",
            "path": str(extract_dir),
            "reason": error,
        }
    return result


def download(arxiv_id: str, output_dir: str = "papers", artifact: str = "both") -> dict:
    """Download paper artifacts and return metadata about the saved files."""
    if artifact not in _ARTIFACT_CHOICES:
        raise ValueError(f"Unsupported artifact: {artifact}")

    clean_id = _normalize_id(arxiv_id)
    safe_id = clean_id.replace("/", "_")

    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, object] = {
        "id": clean_id,
        "artifact": artifact,
        "pdf": {"status": "skipped", "reason": "not requested"},
        "source": {"archive": {"status": "skipped", "reason": "not requested"}, "extract": {"status": "skipped", "reason": "not requested"}},
    }

    pdf_error: str | None = None
    if artifact in {"pdf", "both"}:
        try:
            result["pdf"] = _download_pdf(clean_id, dest_dir, safe_id)
        except Exception as exc:
            pdf_error = str(exc)
            result["pdf"] = {"status": "failed", "reason": pdf_error}

    source_error: str | None = None
    if artifact in {"source", "both"}:
        try:
            result["source"] = _download_source(clean_id, dest_dir, safe_id)
        except Exception as exc:
            source_error = str(exc)
            result["source"] = {
                "archive": {"status": "failed", "reason": source_error},
                "extract": {"status": "skipped", "reason": "source download failed"},
            }

    pdf_ok = isinstance(result["pdf"], dict) and result["pdf"].get("status") == "ok"
    source_ok = isinstance(result["source"], dict) and (
        result["source"].get("archive", {}).get("status") == "ok"
        or result["source"].get("extract", {}).get("status") == "ok"
    )

    if artifact == "pdf":
        if not pdf_ok:
            raise RuntimeError(pdf_error or "PDF download failed")
        result["status"] = "ok"
    elif artifact == "source":
        if not source_ok:
            archive_reason = result["source"].get("archive", {}).get("reason", source_error)
            raise RuntimeError(str(archive_reason or "source download failed"))
        result["status"] = "ok"
    else:
        if not pdf_ok and not source_ok:
            raise RuntimeError("Both PDF and source download failed")
        result["status"] = "ok" if pdf_ok and source_ok else "partial"

    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search and download arXiv papers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search arXiv papers")
    search_parser.add_argument(
        "query",
        help="Search query or arXiv ID (bare ID or id:ARXIV_ID).",
    )
    search_parser.add_argument(
        "--max",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of results (default: 10).",
    )
    search_parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start offset for pagination (default: 0).",
    )

    download_parser = subparsers.add_parser("download", help="Download paper artifacts by arXiv ID")
    download_parser.add_argument(
        "id",
        help="arXiv paper ID, e.g. 2301.07041 or cs/0601001",
    )
    download_parser.add_argument(
        "--dir",
        default="papers",
        metavar="DIR",
        help="Output directory (default: papers).",
    )
    download_parser.add_argument(
        "--artifact",
        choices=_ARTIFACT_CHOICES,
        default="both",
        help="Which artifact to download: pdf, source, or both (default: both).",
    )
    download_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to sleep after download (default: 1.0).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "search":
        results = search(args.query, max_results=args.max, start=args.start)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if args.command == "download":
        result = download(args.id, output_dir=args.dir, artifact=args.artifact)
        time.sleep(args.delay)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
