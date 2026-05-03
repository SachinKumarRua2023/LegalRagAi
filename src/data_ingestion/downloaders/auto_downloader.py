"""
Auto-downloader — fetches US legal case data and saves as mixed file types:
PDF, DOCX, PPTX, XLSX, TXT, JSON, CSV.
This gives a realistic document mix like a real legal research database.
"""
from __future__ import annotations
import json
import csv
import random
import time
from pathlib import Path
from typing import Any

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from config.settings import DATA_RAW_PATH

console = Console()

# ── CourtListener search (public, no auth needed) ────────────────────────────

COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v3/search/"

TOPICS = [
    ("contract breach damages", "contracts"),
    ("fourth amendment search seizure", "criminal"),
    ("first amendment free speech", "constitutional"),
    ("employment discrimination title VII", "employment"),
    ("civil rights section 1983", "civil_rights"),
    ("negligence personal injury tort", "torts"),
    ("intellectual property copyright", "ip"),
    ("immigration asylum deportation", "immigration"),
    ("bankruptcy chapter seven eleven", "bankruptcy"),
    ("family law custody divorce", "family"),
]


def _fetch_opinions(topic: str, count: int = 30) -> list[dict]:
    """Fetch opinion summaries from CourtListener API."""
    results = []
    params = {
        "q": topic,
        "type": "o",
        "stat_Precedential": "on",
        "order_by": "score desc",
        "page_size": min(count, 20),
    }
    try:
        r = requests.get(COURTLISTENER_API, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        # fetch page 2 if need more
        if len(results) < count and data.get("next"):
            r2 = requests.get(data["next"], timeout=20)
            if r2.ok:
                results += r2.json().get("results", [])
    except Exception as e:
        console.print(f"[yellow]  CourtListener fetch warn: {e}[/yellow]")
    return results[:count]


def _opinion_to_text(op: dict) -> str:
    parts = []
    if op.get("case_name"):
        parts.append(f"CASE: {op['case_name']}")
    if op.get("court_citation_string"):
        parts.append(f"COURT: {op['court_citation_string']}")
    if op.get("date_filed"):
        parts.append(f"DATE FILED: {op['date_filed']}")
    if op.get("citation"):
        cites = op["citation"] if isinstance(op["citation"], list) else [op["citation"]]
        parts.append(f"CITATION: {', '.join(str(c) for c in cites)}")
    parts.append("")
    snippet = op.get("snippet", "") or op.get("text", "") or ""
    # strip HTML tags
    import re
    snippet = re.sub(r"<[^>]+>", " ", snippet)
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if snippet:
        parts.append(snippet)
    return "\n".join(parts)


# ── Converters to different file types ───────────────────────────────────────

def _save_as_txt(opinions: list[dict], out_dir: Path, topic_slug: str) -> list[Path]:
    saved = []
    for i, op in enumerate(opinions):
        text = _opinion_to_text(op)
        if len(text) < 50:
            continue
        p = out_dir / f"{topic_slug}_case_{i+1:03d}.txt"
        p.write_text(text, encoding="utf-8")
        saved.append(p)
    return saved


def _save_as_json(opinions: list[dict], out_dir: Path, topic_slug: str) -> list[Path]:
    p = out_dir / f"{topic_slug}_cases.json"
    cleaned = []
    for op in opinions:
        cleaned.append({
            "case_name": op.get("case_name", ""),
            "court": op.get("court_citation_string", ""),
            "date_filed": op.get("date_filed", ""),
            "citation": op.get("citation", ""),
            "snippet": op.get("snippet", ""),
            "absolute_url": op.get("absolute_url", ""),
        })
    p.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    return [p]


def _save_as_docx(opinions: list[dict], out_dir: Path, topic_slug: str) -> list[Path]:
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        return []

    doc = Document()
    doc.add_heading(f"US Legal Cases — {topic_slug.replace('_', ' ').title()}", 0)

    for op in opinions:
        name = op.get("case_name", "Unknown Case")
        doc.add_heading(name, level=1)

        court = op.get("court_citation_string", "")
        date = op.get("date_filed", "")
        if court or date:
            p = doc.add_paragraph()
            run = p.add_run(f"{court}  |  Filed: {date}")
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

        snippet = op.get("snippet", "") or ""
        import re
        snippet = re.sub(r"<[^>]+>", " ", snippet)
        snippet = re.sub(r"\s+", " ", snippet).strip()
        if snippet:
            doc.add_paragraph(snippet)
        doc.add_paragraph()

    p = out_dir / f"{topic_slug}_cases.docx"
    doc.save(str(p))
    return [p]


def _save_as_pptx(opinions: list[dict], out_dir: Path, topic_slug: str) -> list[Path]:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
    except ImportError:
        return []

    import re

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[5]

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"US Legal Cases: {topic_slug.replace('_', ' ').title()}"
    slide.placeholders[1].text = f"{len(opinions)} cases | CompleteRagAI"

    for op in opinions[:15]:  # Max 15 slides per topic
        slide = prs.slides.add_slide(blank_layout)
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(1.0))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = op.get("case_name", "Unknown Case")
        run.font.size = Pt(22)
        run.font.bold = True

        meta = f"{op.get('court_citation_string','')}"
        if op.get("date_filed"):
            meta += f"  |  Filed: {op['date_filed']}"
        txMeta = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(12), Inches(0.4))
        txMeta.text_frame.text = meta
        for para in txMeta.text_frame.paragraphs:
            for run in para.runs:
                run.font.size = Pt(11)

        snippet = re.sub(r"<[^>]+>", " ", op.get("snippet", "") or "")
        snippet = re.sub(r"\s+", " ", snippet).strip()[:500]
        if snippet:
            txSnip = slide.shapes.add_textbox(Inches(0.5), Inches(2.0), Inches(12), Inches(5.0))
            txSnip.text_frame.word_wrap = True
            txSnip.text_frame.text = snippet

    p = out_dir / f"{topic_slug}_cases.pptx"
    prs.save(str(p))
    return [p]


def _save_as_xlsx(all_opinions: dict[str, list[dict]], out_dir: Path) -> list[Path]:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return []

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    headers = ["Case Name", "Court", "Date Filed", "Citation", "Topic", "Snippet"]

    # Summary sheet
    ws_all = wb.create_sheet("All Cases")
    ws_all.append(headers)
    for cell in ws_all[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for topic_slug, opinions in all_opinions.items():
        ws = wb.create_sheet(topic_slug[:30])
        ws.append(headers)
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        for op in opinions:
            import re
            snippet = re.sub(r"<[^>]+>", " ", op.get("snippet", "") or "")
            snippet = re.sub(r"\s+", " ", snippet).strip()[:200]
            row = [
                op.get("case_name", ""),
                op.get("court_citation_string", ""),
                op.get("date_filed", ""),
                str(op.get("citation", "")),
                topic_slug.replace("_", " "),
                snippet,
            ]
            ws.append(row)
            ws_all.append(row)

        ws.column_dimensions["A"].width = 40
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["F"].width = 60

    p = out_dir / "all_cases_summary.xlsx"
    wb.save(str(p))
    return [p]


def _save_as_csv(all_opinions: dict[str, list[dict]], out_dir: Path) -> list[Path]:
    import re
    p = out_dir / "all_cases.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_name", "court", "date_filed", "citation", "topic", "snippet"])
        writer.writeheader()
        for topic_slug, opinions in all_opinions.items():
            for op in opinions:
                snippet = re.sub(r"<[^>]+>", " ", op.get("snippet", "") or "")
                snippet = re.sub(r"\s+", " ", snippet).strip()[:200]
                writer.writerow({
                    "case_name": op.get("case_name", ""),
                    "court": op.get("court_citation_string", ""),
                    "date_filed": op.get("date_filed", ""),
                    "citation": str(op.get("citation", "")),
                    "topic": topic_slug,
                    "snippet": snippet,
                })
    return [p]


# ── Main download function ────────────────────────────────────────────────────

def download_mixed_legal_data(
    cases_per_topic: int = 30,
    output_dir: Path | None = None,
    topics: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Download US legal case data from CourtListener and save as:
    .txt, .json, .docx, .pptx, .xlsx, .csv

    Args:
        cases_per_topic: How many cases to fetch per legal topic
        output_dir: Where to save (default: data/raw/mixed/)
        topics: List of (query, slug) tuples (defaults to 10 built-in topics)
    """
    output_dir = output_dir or (DATA_RAW_PATH / "mixed")
    output_dir.mkdir(parents=True, exist_ok=True)

    topics = topics or TOPICS
    all_opinions: dict[str, list[dict]] = {}
    saved_files: list[str] = []

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Downloading legal cases...", total=len(topics))

        for query, slug in topics:
            progress.update(task, description=f"Fetching: {slug}")
            slug_dir = output_dir / slug
            slug_dir.mkdir(exist_ok=True)

            opinions = _fetch_opinions(query, count=cases_per_topic)
            if not opinions:
                progress.advance(task)
                continue

            all_opinions[slug] = opinions

            # Save each topic in multiple formats
            for fp in _save_as_txt(opinions, slug_dir, slug):
                saved_files.append(str(fp))
            for fp in _save_as_json(opinions, slug_dir, slug):
                saved_files.append(str(fp))
            for fp in _save_as_docx(opinions, slug_dir, slug):
                saved_files.append(str(fp))
            for fp in _save_as_pptx(opinions, slug_dir, slug):
                saved_files.append(str(fp))

            console.print(f"  [green]✓[/green] {slug}: {len(opinions)} cases → {slug_dir}")
            time.sleep(0.3)
            progress.advance(task)

    # Cross-topic files (XLSX + CSV with everything)
    if all_opinions:
        for fp in _save_as_xlsx(all_opinions, output_dir):
            saved_files.append(str(fp))
        for fp in _save_as_csv(all_opinions, output_dir):
            saved_files.append(str(fp))

    total_cases = sum(len(v) for v in all_opinions.values())
    console.print(f"\n[bold green]✓ Download complete![/bold green]")
    console.print(f"  Topics: {len(all_opinions)}")
    console.print(f"  Cases: {total_cases}")
    console.print(f"  Files: {len(saved_files)}")
    console.print(f"  Location: {output_dir}")

    return {
        "status": "ok",
        "output_dir": str(output_dir),
        "topics": len(all_opinions),
        "total_cases": total_cases,
        "files_created": len(saved_files),
        "file_types": ["txt", "json", "docx", "pptx", "xlsx", "csv"],
    }
