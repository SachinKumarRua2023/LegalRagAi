"""
HuggingFace dataset downloader for US legal cases.
Uses free public datasets — no token required for most.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import track

from config.settings import DATA_RAW_PATH

console = Console()

# Free legal datasets on HuggingFace
LEGAL_DATASETS = {
    "legal_case_reports": {
        "hf_name": "pile-of-law/pile-of-law",
        "subset": "courtlistener_opinions",
        "split": "train",
        "text_field": "text",
        "description": "US Court opinions from CourtListener",
        "est_size_gb": 2.0,
    },
    "us_scotus": {
        "hf_name": "coastalcph/fairlex",
        "subset": "scotus",
        "split": "train",
        "text_field": "text",
        "description": "US Supreme Court cases",
        "est_size_gb": 0.1,
    },
    "legal_contracts": {
        "hf_name": "pile-of-law/pile-of-law",
        "subset": "atticus_contracts",
        "split": "train",
        "text_field": "text",
        "description": "US Legal contracts",
        "est_size_gb": 0.5,
    },
}


def download_hf_dataset(
    dataset_key: str = "us_scotus",
    max_records: int = 5000,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Download a HuggingFace legal dataset and save as JSON files.

    Args:
        dataset_key: Key from LEGAL_DATASETS dict
        max_records: Max records to save
        output_dir: Where to save (defaults to data/raw/huggingface/<dataset_key>/)
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise RuntimeError("Run: pip install datasets")

    if dataset_key not in LEGAL_DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_key}. Options: {list(LEGAL_DATASETS.keys())}")

    cfg = LEGAL_DATASETS[dataset_key]
    output_dir = output_dir or (DATA_RAW_PATH / "huggingface" / dataset_key)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Loading HF dataset: {cfg['hf_name']} ({cfg['description']})[/cyan]")
    console.print("[yellow]This may take a few minutes for large datasets...[/yellow]")

    try:
        ds = load_dataset(
            cfg["hf_name"],
            cfg.get("subset"),
            split=cfg.get("split", "train"),
            streaming=True,  # Stream to avoid downloading everything
            trust_remote_code=True,
        )
    except Exception as e:
        console.print(f"[red]Failed to load {cfg['hf_name']}: {e}[/red]")
        return {"status": "error", "error": str(e)}

    text_field = cfg["text_field"]
    saved = 0
    batch = []
    batch_size = 100

    for i, record in enumerate(ds):
        if saved >= max_records:
            break

        text = record.get(text_field, "") or ""
        if not text.strip() or len(text) < 100:
            continue

        meta = {k: v for k, v in record.items() if k != text_field and isinstance(v, (str, int, float, bool))}
        meta["source_dataset"] = cfg["hf_name"]
        meta["dataset_key"] = dataset_key

        batch.append({"text": text, "metadata": meta})

        if len(batch) >= batch_size:
            fname = output_dir / f"batch_{saved // batch_size:05d}.json"
            fname.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
            batch = []
            console.print(f"  Saved batch {saved // batch_size} ({saved + batch_size} records)")

        saved += 1

    if batch:
        fname = output_dir / f"batch_{saved // batch_size:05d}.json"
        fname.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")

    console.print(f"[green]✓ Saved {saved} records to {output_dir}[/green]")
    return {
        "source": "huggingface",
        "dataset": cfg["hf_name"],
        "records": saved,
        "output_dir": str(output_dir),
    }


def download_scotus_cases(max_records: int = 2000) -> dict[str, Any]:
    """Download US Supreme Court cases — best starting point, ~100MB."""
    return download_hf_dataset("us_scotus", max_records=max_records)


def download_all_legal_data(
    max_gb: float = 2.0,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Download a comprehensive legal dataset up to max_gb.
    Uses streaming so you only download what you need.
    """
    targets = [
        ("us_scotus", 3000),
        ("legal_contracts", 5000),
    ]

    results = []
    for key, limit in targets:
        result = download_hf_dataset(key, max_records=limit, output_dir=output_dir)
        results.append(result)

    return {"datasets_downloaded": len(results), "results": results}
