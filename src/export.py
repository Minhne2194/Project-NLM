from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.schemas import FlashcardSet, QuizSet, RagAnswer, Summary

ExportFormat = Literal["text", "md", "json"]


def _to_markdown(model: BaseModel) -> str:
    lines: list[str] = []

    if isinstance(model, RagAnswer):
        lines.append(f"# Câu hỏi: {model.question}\n")
        lines.append("## Câu trả lời\n")
        lines.append(f"{model.answer}\n")
        if model.citations:
            lines.append("## Nguồn trích dẫn\n")
            for c in model.citations:
                lines.append(
                    f"- **[{c.source_marker}]** File: `{c.filename}` (Trang {c.page})"
                )

    elif isinstance(model, Summary):
        lines.append(f"# Tóm tắt tài liệu ({model.scope}: {model.target or 'Toàn bộ'})\n")
        lines.append("## Tổng quan\n")
        lines.append(f"{model.summary}\n")
        if model.key_points:
            lines.append("## Các ý chính\n")
            for kp in model.key_points:
                lines.append(f"- {kp}")
            lines.append("")
        if model.citations:
            lines.append("## Nguồn tham khảo\n")
            for c in model.citations:
                lines.append(
                    f"- **[{c.source_marker}]** File: `{c.filename}` (Trang {c.page})"
                )

    elif isinstance(model, QuizSet):
        lines.append(f"# Bộ câu hỏi trắc nghiệm ({len(model.items)} câu)\n")
        for i, item in enumerate(model.items, start=1):
            lines.append(f"### Câu {i}: {item.question}\n")
            for j, opt in enumerate(item.options):
                prefix = chr(65 + j)  # A, B, C, D
                marker = "✓ " if j == item.correct_index else "  "
                lines.append(f"- [{marker}] {prefix}. {opt}")
            lines.append(f"\n> **Đáp án đúng:** {chr(65 + item.correct_index)}")
            lines.append(f"> **Giải thích:** {item.explanation}")
            if item.source_markers:
                lines.append(f"> **Nguồn:** {', '.join(item.source_markers)}")
            lines.append("")

    elif isinstance(model, FlashcardSet):
        lines.append(f"# Bộ thẻ ghi nhớ Flashcards ({len(model.cards)} thẻ)\n")
        for i, card in enumerate(model.cards, start=1):
            lines.append(f"### Thẻ {i}: {card.topic or 'Kiến thức cốt lõi'}\n")
            lines.append(f"- **Mặt trước (Front):** {card.front}")
            lines.append(f"- **Mặt sau (Back):** {card.back}")
            if card.hint:
                lines.append(f"- **Gợi ý (Hint):** {card.hint}")
            if card.source_markers:
                lines.append(f"- **Nguồn:** {', '.join(card.source_markers)}")
            lines.append("")

    else:
        lines.append(model.model_dump_json(indent=2))

    return "\n".join(lines).strip() + "\n"


def export(
    model: BaseModel,
    *,
    fmt: ExportFormat = "text",
    output: Path | str | None = None,
) -> str | Path:
    if fmt == "json":
        text = model.model_dump_json(indent=2) + "\n"
    elif fmt in {"text", "md"}:
        text = _to_markdown(model)
    else:
        raise ValueError(f"Unknown fmt '{fmt}'. Expected 'text' | 'md' | 'json'.")

    if output is None:
        return text

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path
