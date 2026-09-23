import json
from typing import Type

from pydantic import BaseModel, ValidationError

from src.config import settings
from src.llm import invoke_llm
from src.rag import (
    fetch_all_chunks,
    format_citations,
    render_prompt,
    retrieve,
)
from src.schemas import Flashcard, FlashcardSet, QuizItem, QuizSet, Summary

SUMMARY_SINGLE_TEMPLATE = "summary_single.jinja2"
SUMMARY_MAP_TEMPLATE = "summary_map.jinja2"
SUMMARY_REDUCE_TEMPLATE = "summary_reduce.jinja2"
QUIZ_TEMPLATE = "quiz.jinja2"
FLASHCARDS_TEMPLATE = "flashcards.jinja2"


def _resolve_target(document, query, filters, k, retrieval_k):
    effective_filters = dict(filters or {})

    if document:
        effective_filters["filename"] = document

    if query:
        chunks = retrieve(query, k=k or retrieval_k, filters=effective_filters)
        return chunks, "query", query

    if effective_filters:
        chunks = fetch_all_chunks(filters=effective_filters)
        scope = "document" if document else "filter"
        target = ", ".join(f"{k}={v}" for k, v in effective_filters.items())
        return chunks, scope, target

    return fetch_all_chunks(filters=None), "corpus", None


def _parse_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        start_idx = min(
            [i for i in [cleaned.find("{"), cleaned.find("[")] if i != -1],
            default=-1,
        )
        end_idx = max([cleaned.rfind("}"), cleaned.rfind("]")], default=-1)
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            obj = json.loads(cleaned[start_idx : end_idx + 1])
        else:
            raise RuntimeError(f"Expected JSON object or array. Raw: {text[:200]}")

    if not isinstance(obj, (dict, list)):
        raise RuntimeError("Expected JSON object or array.")
    return obj


def _validate_summary_payload(payload: dict) -> tuple[str, list[str]]:
    if not isinstance(payload, dict):
        raise RuntimeError("Summary payload must be a JSON object.")
    summary = payload.get("summary", "")
    key_points = payload.get("key_points", [])
    if not isinstance(key_points, list):
        key_points = []
    return str(summary), [str(kp) for kp in key_points]


def _validate_items(
    payload: dict,
    key: str,
    model_class: Type[BaseModel],
    dedup_field: str,
    label: str,
    valid_markers: set[str],
):
    raw_items = (
        payload.get(key)
        if isinstance(payload, dict)
        else (payload if isinstance(payload, list) else [])
    )
    if not isinstance(raw_items, list):
        raw_items = []

    items, seen = [], set()

    for raw in raw_items:
        try:
            item = model_class.model_validate(raw)
        except ValidationError:
            continue

        norm = str(getattr(item, dedup_field, "")).strip().lower()
        if not norm or norm in seen:
            continue

        seen.add(norm)
        markers = [m for m in getattr(item, "source_markers", []) if m in valid_markers]
        items.append(item.model_copy(update={"source_markers": markers}))

    if not items:
        raise RuntimeError(f"No valid {label} produced.")
    return items


def summarize(
    document: str | None = None,
    query: str | None = None,
    filters: dict | None = None,
    k: int | None = None,
) -> Summary:
    chunks, scope, target = _resolve_target(
        document, query, filters, k, settings.summarize_retrieval_k
    )

    if not chunks:
        return Summary(
            scope=scope,
            target=target,
            summary="Không tìm thấy tài liệu phù hợp để tóm tắt.",
            key_points=[],
            citations=[],
            chunks=[],
        )

    if len(chunks) <= settings.summarize_batch_size:
        prompt = render_prompt(SUMMARY_SINGLE_TEMPLATE, chunks=chunks)
        payload = _parse_json(invoke_llm(prompt))
        summary_text, key_points = _validate_summary_payload(payload)
    else:
        partials = []
        for start in range(0, len(chunks), settings.summarize_batch_size):
            batch = chunks[start : start + settings.summarize_batch_size]
            payload = _parse_json(
                invoke_llm(render_prompt(SUMMARY_MAP_TEMPLATE, chunks=batch))
            )
            summary_text, key_points = _validate_summary_payload(payload)
            partials.append({"summary": summary_text, "key_points": key_points})

        payload = _parse_json(
            invoke_llm(render_prompt(SUMMARY_REDUCE_TEMPLATE, partials=partials))
        )
        summary_text, key_points = _validate_summary_payload(payload)

    return Summary(
        scope=scope,
        target=target,
        summary=summary_text,
        key_points=key_points,
        citations=format_citations(chunks),
        chunks=chunks,
    )


def generate_quiz(
    document: str | None = None,
    query: str | None = None,
    filters: dict | None = None,
    count: int | None = None,
    k: int | None = None,
) -> QuizSet:
    chunks, scope, target = _resolve_target(
        document, query, filters, k, settings.generation_retrieval_k
    )

    if not chunks:
        return QuizSet(
            scope=scope,
            target=target,
            items=[],
            citations=[],
            chunks=[],
        )

    n = count or settings.quiz_default_count
    valid_markers = {f"S{i}" for i in range(1, len(chunks) + 1)}
    prompt = render_prompt(QUIZ_TEMPLATE, chunks=chunks, count=n)
    payload = _parse_json(invoke_llm(prompt))

    items = _validate_items(
        payload, "items", QuizItem, "question", "quiz items", valid_markers
    )

    return QuizSet(
        scope=scope,
        target=target,
        items=items,
        chunks=chunks,
        citations=format_citations(chunks),
    )


def generate_flashcards(
    document: str | None = None,
    query: str | None = None,
    filters: dict | None = None,
    count: int | None = None,
    k: int | None = None,
) -> FlashcardSet:
    chunks, scope, target = _resolve_target(
        document, query, filters, k, settings.generation_retrieval_k
    )

    if not chunks:
        return FlashcardSet(
            scope=scope,
            target=target,
            cards=[],
            citations=[],
            chunks=[],
        )

    n = count or settings.flashcards_default_count
    valid_markers = {f"S{i}" for i in range(1, len(chunks) + 1)}
    prompt = render_prompt(FLASHCARDS_TEMPLATE, chunks=chunks, count=n)
    payload = _parse_json(invoke_llm(prompt))

    cards = _validate_items(
        payload, "cards", Flashcard, "front", "flashcards", valid_markers
    )

    return FlashcardSet(
        scope=scope,
        target=target,
        cards=cards,
        chunks=chunks,
        citations=format_citations(chunks),
    )
