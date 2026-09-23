from functools import lru_cache

from sentence_transformers import CrossEncoder

from src.llm import invoke_llm
from src.rag import ANSWER_TEMPLATE, format_citations, render_prompt, retrieve
from src.schemas import RagAnswer

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def get_reranker(model_name: str = RERANKER_MODEL) -> CrossEncoder:
    return CrossEncoder(model_name)


def answer_with_reranker(
    question: str,
    collection_name: str | None = None,
    reranker: CrossEncoder | None = None,
    initial_k: int = 15,
    rerank_k: int = 5,
    filters: dict | None = None,
) -> RagAnswer:
    # Giai đoạn 1: Truy xuất thô (initial_k)
    chunks = retrieve(
        question, k=initial_k, filters=filters, collection_name=collection_name
    )
    if not chunks:
        return RagAnswer(
            question=question,
            answer="Tôi không có đủ thông tin trong ngữ cảnh được cung cấp để trả lời.",
        )

    # Giai đoạn 2: Tính toán điểm số tương quan chéo bằng Cross-Encoder
    if reranker is None:
        reranker = get_reranker()

    scores = reranker.predict([[question, chunk.text] for chunk in chunks])
    for chunk, score in zip(chunks, scores):
        chunk.score = float(score)

    # Xếp hạng lại và lọc ra các đoạn liên quan nhất (rerank_k)
    reranked = sorted(chunks, key=lambda c: c.score, reverse=True)[:rerank_k]

    # Đưa ngữ cảnh đã được lọc vào prompt cho LLM
    prompt = render_prompt(ANSWER_TEMPLATE, question=question, chunks=reranked)
    text = invoke_llm(prompt)

    return RagAnswer(
        question=question,
        answer=text.strip(),
        citations=format_citations(reranked),
        chunks=reranked,
    )
