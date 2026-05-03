"""
ingest.py — Data ingestion entry point.

Usage:
    python ingest.py                        # Index all files in data/raw/
    python ingest.py --path ./data/uploads  # Index a specific folder
    python ingest.py --file ./myfile.pdf    # Index a single file
    python ingest.py --download courtlistener --query "criminal law" --limit 500
    python ingest.py --download huggingface --dataset us_scotus --limit 2000
    python ingest.py --status              # Show index status
"""
import sys
import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="CompleteRagAI — Data Ingestion Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--path", type=str, help="Directory to index")
    parser.add_argument("--file", type=str, help="Single file to index")
    parser.add_argument("--download", choices=["courtlistener", "huggingface", "all", "auto"], help="Download source. 'auto' downloads mixed file types (PDF/DOCX/PPTX/XLSX/CSV/TXT) from CourtListener")
    parser.add_argument("--query", type=str, default="legal case usa", help="Search query for CourtListener")
    parser.add_argument("--dataset", type=str, default="us_scotus", help="HuggingFace dataset key")
    parser.add_argument("--limit", type=int, default=500, help="Max records to download")
    parser.add_argument("--status", action="store_true", help="Show index status and exit")
    args = parser.parse_args()

    console.print(Panel("[bold cyan]CompleteRagAI — Ingestion Tool[/bold cyan]", border_style="cyan"))

    if args.status:
        from src.vector_db.indexer import get_index_status
        status = get_index_status()
        console.print(status)
        return

    # ── Download ──────────────────────────────────────────────────────────────
    if args.download == "auto":
        from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
        from src.vector_db.indexer import index_directory
        from config.settings import DATA_RAW_PATH
        console.print("[cyan]Downloading mixed legal data (TXT, JSON, DOCX, PPTX, XLSX, CSV)...[/cyan]")
        result = download_mixed_legal_data(cases_per_topic=args.limit // 10 or 30)
        console.print(f"[green]Downloaded: {result['total_cases']} cases, {result['files_created']} files[/green]")
        console.print("[cyan]Indexing all downloaded files...[/cyan]")
        idx = index_directory(DATA_RAW_PATH / "mixed")
        console.print(f"[green]Indexed: {idx['indexed']} files, {idx['collection_total_chunks']} total chunks[/green]")
        return

    if args.download:
        if args.download in ("courtlistener", "all"):
            from src.data_ingestion.downloaders.courtlistener_downloader import download_opinions
            console.print("[cyan]Downloading from CourtListener...[/cyan]")
            result = download_opinions(query=args.query, max_records=args.limit)
            console.print(f"[green]Downloaded: {result}[/green]")

            # Auto-index downloaded files
            from src.vector_db.indexer import index_directory
            from config.settings import DATA_RAW_PATH
            console.print("[cyan]Indexing downloaded files...[/cyan]")
            idx = index_directory(DATA_RAW_PATH / "courtlistener")
            console.print(f"[green]Indexed: {idx['indexed']} files, {idx['collection_total_chunks']} total chunks[/green]")

        if args.download in ("huggingface", "all"):
            from src.data_ingestion.downloaders.huggingface_downloader import download_hf_dataset
            console.print(f"[cyan]Downloading HuggingFace dataset: {args.dataset}...[/cyan]")
            result = download_hf_dataset(dataset_key=args.dataset, max_records=args.limit)
            console.print(f"[green]Downloaded: {result}[/green]")

            # Auto-index
            from src.vector_db.indexer import index_directory
            from config.settings import DATA_RAW_PATH
            idx_dir = DATA_RAW_PATH / "huggingface" / args.dataset
            if idx_dir.exists():
                console.print("[cyan]Indexing downloaded files...[/cyan]")
                idx = index_directory(idx_dir)
                console.print(f"[green]Indexed: {idx['indexed']} files[/green]")
        return

    # ── Index files ───────────────────────────────────────────────────────────
    if args.file:
        from src.vector_db.indexer import index_file
        console.print(f"[cyan]Indexing file: {args.file}[/cyan]")
        result = index_file(args.file)
        console.print(f"[green]{result}[/green]")
        return

    if args.path:
        from src.vector_db.indexer import index_directory
        console.print(f"[cyan]Indexing directory: {args.path}[/cyan]")
        result = index_directory(args.path)
        console.print(f"[green]Done: {result['indexed']} files, {result['collection_total_chunks']} total chunks[/green]")
        return

    # Default: index all of data/raw
    from src.vector_db.indexer import index_directory
    from config.settings import DATA_RAW_PATH
    console.print(f"[cyan]Indexing all files in: {DATA_RAW_PATH}[/cyan]")
    result = index_directory(DATA_RAW_PATH)
    console.print(f"[green]Done: {result['indexed']} files indexed, {result['collection_total_chunks']} total chunks[/green]")


if __name__ == "__main__":
    main()
