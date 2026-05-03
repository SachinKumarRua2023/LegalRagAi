"""
main.py — Interactive Legal AI Agent entry point.

Usage:
    python main.py                      # Interactive REPL
    python main.py --query "What is..."  # Single query
    python main.py --query "..." --file case.pdf   # Query in specific file
    python main.py --query "..." --folder ./data/raw/criminal
    python main.py --status             # Index status
"""
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def ensure_data_available():
    """
    Auto-download and index sample legal data on first run.
    Downloads 1-3GB of mixed legal cases (SCOTUS, CaseHOLD) when vector DB is empty.
    """
    from src.vector_db.indexer import get_index_status, index_directory
    from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
    from config.settings import DATA_RAW_PATH
    from rich.progress import Progress, SpinnerColumn, TextColumn

    status = get_index_status()
    total_chunks = status.get("total_chunks", 0)

    if total_chunks > 0:
        console.print(f"[green]✓ Vector DB ready: {total_chunks} chunks indexed[/green]")
        return

    # Vector DB is empty - download and index sample data
    console.print(Panel(
        "[bold yellow]First Run: Downloading Sample Legal Data[/bold yellow]\n"
        "This will download ~1-3GB of US legal cases (SCOTUS + CaseHOLD)\n"
        "and index them for semantic search. This only happens once.",
        border_style="yellow"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Download phase - fetch substantial data (1-3GB worth)
        task = progress.add_task("[cyan]Downloading legal cases...", total=None)

        # Download ~3000 cases total (1500 SCOTUS + 1500 CaseHOLD) = ~1-3GB
        result = download_mixed_legal_data(cases_per_topic=1500)

        progress.update(task, completed=True, description=f"[green]Downloaded {result['total_cases']} cases[/green]")

        # Indexing phase
        task2 = progress.add_task("[cyan]Indexing to vector database...", total=None)

        idx_result = index_directory(DATA_RAW_PATH / "mixed", recursive=True)

        progress.update(task2, completed=True, description=f"[green]Indexed {idx_result['indexed']} files[/green]")

    # Final status
    final_status = get_index_status()
    console.print(Panel(
        f"[bold green]✓ Setup Complete![/bold green]\n"
        f"• Cases downloaded: {result['total_cases']}\n"
        f"• Files created: {result['files_created']}\n"
        f"• Total chunks indexed: {final_status.get('total_chunks', 0)}\n"
        f"• Unique files: {final_status.get('unique_files', 0)}\n\n"
        f"[dim]Data location: {DATA_RAW_PATH / 'mixed'}[/dim]\n"
        f"[dim]Vector DB: {final_status.get('db_path', 'chroma_db/')}[/dim]",
        border_style="green"
    ))


def main():
    parser = argparse.ArgumentParser(
        description="CompleteRagAI — Legal AI Research Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--query", "-q", type=str, help="Run a single query and exit")
    parser.add_argument("--file", "-f", type=str, help="Restrict search to this file name")
    parser.add_argument("--folder", type=str, help="Restrict search to this folder path")
    parser.add_argument("--type", type=str, help="Filter by file type (pdf, docx, etc.)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    parser.add_argument("--status", action="store_true", help="Show index status and exit")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    args = parser.parse_args()

    if args.no_color:
        import os
        os.environ["NO_COLOR"] = "1"

    if args.status:
        from src.vector_db.indexer import get_index_status
        status = get_index_status()
        console.print_json(data=status)
        return

    # Auto-install sample data on first run if vector DB is empty
    ensure_data_available()

    if args.query:
        # Single-shot query mode
        from src.rag.pipeline import query, format_response
        result = query(
            question=args.query,
            n_results=args.top_k,
            filter_file=args.file,
            filter_folder=args.folder,
            filter_file_type=getattr(args, "type", None),
            verbose=True,
        )
        console.print(format_response(result))
        return

    # Interactive REPL mode
    from src.agents.legal_agent import LegalAgent
    agent = LegalAgent()
    agent.run_interactive()


if __name__ == "__main__":
    main()
