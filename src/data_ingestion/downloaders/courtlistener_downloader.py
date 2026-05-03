"""
CourtListener API downloader — free, no auth required for basic search.
Docs: https://www.courtlistener.com/api/rest/v3/
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import DATA_RAW_PATH, COURTLISTENER_TOKEN, DOWNLOAD_BATCH_SIZE

console = Console()

BASE_URL = "https://www.courtlistener.com/api/rest/v3"
HEADERS = {"Authorization": f"Token {COURTLISTENER_TOKEN}"} if COURTLISTENER_TOKEN else {}

# Courts to target (federal + major state)
TARGET_COURTS = [
    "scotus",   # US Supreme Court
    "ca1", "ca2", "ca3", "ca4", "ca5", "ca6", "ca7", "ca8", "ca9", "ca10", "ca11",  # Circuit courts
    "dcd",      # DC District
    "nyed", "casd", "ilnd",  # Major districts
]


def _get(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _save_case(case: dict, output_dir: Path) -> Path | None:
    """Save a single case as JSON."""
    case_id = case.get("id", "unknown")
    fname = f"case_{case_id}.json"
    fpath = output_dir / fname
    fpath.write_text(json.dumps(case, indent=2, ensure_ascii=False), encoding="utf-8")
    return fpath


def _save_opinion_text(opinion: dict, output_dir: Path, case_id: str) -> Path | None:
    """Save opinion plain text as .txt file."""
    text = (
        opinion.get("plain_text")
        or opinion.get("html_with_citations")
        or opinion.get("html")
        or ""
    )
    if not text.strip():
        return None
    fpath = output_dir / f"opinion_{case_id}_{opinion.get('id','0')}.txt"
    # Strip basic HTML tags if present
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    fpath.write_text(text.strip(), encoding="utf-8")
    return fpath


def download_opinions(
    query: str = "legal case",
    max_records: int = 500,
    output_dir: Path | None = None,
    court: str | None = None,
) -> dict[str, Any]:
    """
    Download case opinions from CourtListener free API.

    Args:
        query: Search query (e.g., "contract dispute", "civil rights", "criminal")
        max_records: Max number of opinions to download
        output_dir: Where to save files (defaults to data/raw/courtlistener/)
        court: Filter by court ID (e.g., "scotus", "ca9")

    Returns: Summary dict with counts and paths
    """
    output_dir = output_dir or (DATA_RAW_PATH / "courtlistener")
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Downloading from CourtListener: '{query}' (max {max_records})[/cyan]")

    params: dict = {
        "q": query,
        "type": "o",          # opinions
        "order_by": "score desc",
        "stat_Precedential": "on",
        "page_size": min(DOWNLOAD_BATCH_SIZE, 20),  # API max per page
    }
    if court:
        params["court"] = court

    saved_files = []
    page_url = f"{BASE_URL}/search/"
    total_downloaded = 0

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Downloading opinions...", total=max_records)

        while page_url and total_downloaded < max_records:
            try:
                data = _get(page_url, params if "search" in page_url else None)
            except requests.HTTPError as e:
                console.print(f"[red]API error: {e}[/red]")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                if total_downloaded >= max_records:
                    break
                fp = _save_case(item, output_dir)
                if fp:
                    saved_files.append(str(fp))

                # Also fetch and save full opinion text
                opinion_url = item.get("opinions")
                if opinion_url and isinstance(opinion_url, str):
                    try:
                        op_data = _get(opinion_url)
                        for op in op_data.get("results", []):
                            tp = _save_opinion_text(op, output_dir, str(item.get("id", "?")))
                            if tp:
                                saved_files.append(str(tp))
                    except Exception:
                        pass

                total_downloaded += 1
                progress.update(task, advance=1, description=f"Downloaded {total_downloaded} opinions")
                time.sleep(0.1)  # Be polite to the API

            page_url = data.get("next")
            params = None  # next URL already has params

    console.print(f"[green]✓ Downloaded {total_downloaded} opinions → {output_dir}[/green]")
    return {
        "source": "courtlistener",
        "query": query,
        "downloaded": total_downloaded,
        "files": len(saved_files),
        "output_dir": str(output_dir),
    }


def download_bulk_sample(max_gb: float = 1.0) -> dict[str, Any]:
    """
    Download a broad sample of US legal cases across multiple topics.
    Targets ~1GB of text data.
    """
    topics = [
        ("contract law", 200),
        ("criminal defense fourth amendment", 200),
        ("civil rights section 1983", 200),
        ("employment discrimination", 150),
        ("immigration asylum", 150),
        ("intellectual property patent", 150),
        ("personal injury tort negligence", 150),
        ("constitutional law first amendment", 150),
        ("bankruptcy chapter 7 11", 100),
        ("family law custody divorce", 100),
    ]

    total_result = {"source": "courtlistener", "total_downloaded": 0, "topics": []}

    for topic, count in topics:
        result = download_opinions(query=topic, max_records=count)
        total_result["total_downloaded"] += result["downloaded"]
        total_result["topics"].append(result)

    return total_result
