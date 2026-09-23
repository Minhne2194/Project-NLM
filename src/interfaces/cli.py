import json
import sys
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows terminal
if sys.platform.startswith("win"):
    import io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.panel import Panel

from src.export import ExportFormat, export
from src.indexing import ingest as ingest_data_dir
from src.learning import generate_flashcards, generate_quiz, summarize as summarize_learning
from src.rag import answer, retrieve
from src.schemas import RetrievedChunk

app = typer.Typer(
    name="nlm",
    help="Simple NotebookLM: Grounded Q&A, Summarization, Quiz, and Flashcards.",
)
console = Console(legacy_windows=False)


def _parse_filters(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    out = {}
    for part in raw.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            k, v = k.strip(), v.strip()
            out[k] = int(v) if v.isdigit() else v
    return out or None


def _print_answer(ans: str):
    console.print(Panel(ans, title="[bold green]Câu trả lời[/bold green]", expand=False))


def _print_sources(chunks: list[RetrievedChunk]):
    if not chunks:
        return
    console.print("\n[bold cyan]Nguồn trích dẫn:[/bold cyan]")
    for i, c in enumerate(chunks, start=1):
        console.print(
            f"  [bold yellow][S{i}][/bold yellow] [underline]{c.metadata.filename}[/underline] "
            f"(Trang {c.metadata.page}) [dim]score={c.score:.3f}[/dim]"
        )


def _emit(model, output: Optional[str], fmt: str):
    res = export(model, fmt=fmt, output=output)
    if output:
        console.print(f"[bold green]Đã xuất ra:[/bold green] {output}")
    else:
        console.print(res)


@app.command()
def ingest(
    recreate: bool = typer.Option(
        False, "--recreate", "-r", help="Recreate collection before indexing"
    )
):
    """Index tất cả file PDF trong data/ vào Qdrant."""
    with console.status("[bold green]Đang index tài liệu...[/bold green]"):
        import httpx
        from src.config import settings
        api_available = False
        try:
            r = httpx.get(f"{settings.api_url}/health", timeout=2.0)
            if r.status_code == 200:
                api_available = True
        except Exception:
            pass

        if api_available:
            resp = httpx.post(f"{settings.api_url}/ingest?recreate={str(recreate).lower()}", timeout=300.0)
            if resp.status_code == 200:
                count = resp.json().get("chunks_indexed", 0)
            else:
                console.print(f"[bold red]Lỗi từ API:[/bold red] {resp.text}")
                return
        else:
            count = ingest_data_dir(recreate=recreate)

    console.print(f"[bold green]Xong.[/bold green] Đã index [bold]{count}[/bold] chunks.")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Câu hỏi cần trả lời"),
    k: Optional[int] = typer.Option(None, "-k", help="Số lượng chunks truy xuất"),
    filters: Optional[str] = typer.Option(
        None, "--filters", "-f", help="Bộ lọc (ví dụ: 'filename=doc.pdf,page=2')"
    ),
):
    """Hỏi đáp có trích dẫn nguồn dựa trên tài liệu."""
    filt = _parse_filters(filters)
    result = answer(question, k=k, filters=filt)
    _print_answer(result.answer)
    _print_sources(result.chunks)


@app.command("debug-retrieval")
def debug_retrieval(
    question: str = typer.Argument(..., help="Truy vấn kiểm tra retrieval"),
    k: Optional[int] = typer.Option(5, "-k", help="Số chunk lấy về"),
    filters: Optional[str] = typer.Option(None, "--filters", "-f"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Kiểm tra kết quả semantic search mà không gọi LLM."""
    filt = _parse_filters(filters)
    chunks = retrieve(question, k=k, filters=filt)
    if as_json:
        console.print(
            json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2)
        )
    else:
        _print_sources(chunks)


@app.command()
def summarize(
    document: Optional[str] = typer.Option(None, "--document", "-d"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    filters: Optional[str] = typer.Option(None, "--filters", "-f"),
    k: Optional[int] = typer.Option(None, "-k"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
    fmt: str = typer.Option("text", "--fmt", help="text | md | json"),
):
    """Tóm tắt tài liệu theo chiến lược Single hoặc Map-Reduce."""
    filt = _parse_filters(filters)
    result = summarize_learning(
        document=document, query=query, filters=filt, k=k
    )
    _emit(result, output, fmt)


@app.command()
def quiz(
    document: Optional[str] = typer.Option(None, "--document", "-d"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    filters: Optional[str] = typer.Option(None, "--filters", "-f"),
    count: Optional[int] = typer.Option(None, "--count", "-c"),
    k: Optional[int] = typer.Option(None, "-k"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
    fmt: str = typer.Option("text", "--fmt", help="text | md | json"),
):
    """Tạo bộ câu hỏi trắc nghiệm từ tài liệu."""
    filt = _parse_filters(filters)
    result = generate_quiz(
        document=document, query=query, filters=filt, count=count, k=k
    )
    _emit(result, output, fmt)


@app.command()
def flashcards(
    document: Optional[str] = typer.Option(None, "--document", "-d"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    filters: Optional[str] = typer.Option(None, "--filters", "-f"),
    count: Optional[int] = typer.Option(None, "--count", "-c"),
    k: Optional[int] = typer.Option(None, "-k"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
    fmt: str = typer.Option("text", "--fmt", help="text | md | json"),
):
    """Tạo bộ thẻ flashcards ôn tập kiến thức."""
    filt = _parse_filters(filters)
    result = generate_flashcards(
        document=document, query=query, filters=filt, count=count, k=k
    )
    _emit(result, output, fmt)


if __name__ == "__main__":
    app()
