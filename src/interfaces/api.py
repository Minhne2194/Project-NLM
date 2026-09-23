from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.filters import MetadataFilter, filters_to_dict
from src.indexing import save_and_ingest_pdf
from src.learning import generate_flashcards, generate_quiz, summarize
from src.rag import answer, fetch_all_chunks
from src.schemas import FlashcardSet, QuizSet, RagAnswer, Summary


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=64)
    filters: MetadataFilter | None = None


class SummarizeRequest(BaseModel):
    document: str | None = None
    query: str | None = None
    filters: MetadataFilter | None = None
    k: int | None = Field(default=None, ge=1, le=64)


class QuizRequest(BaseModel):
    document: str | None = None
    query: str | None = None
    filters: MetadataFilter | None = None
    count: int | None = Field(default=None, ge=1, le=50)
    k: int | None = Field(default=None, ge=1, le=64)


class FlashcardsRequest(QuizRequest):
    pass


class DocumentInfo(BaseModel):
    filename: str
    document_id: str
    total_pages: int
    total_chunks: int


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int


app = FastAPI(
    title="RAG Learning API",
    description="Grounded Q&A, summaries, quizzes, and flashcards over indexed PDFs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def list_documents() -> list[DocumentInfo]:
    chunks = fetch_all_chunks(filters=None)
    doc_map: dict[str, dict[str, Any]] = {}

    for c in chunks:
        fn = c.metadata.filename
        if fn not in doc_map:
            doc_map[fn] = {
                "filename": fn,
                "document_id": c.metadata.document_id,
                "pages": set(),
                "chunks": 0,
            }
        doc_map[fn]["pages"].add(c.metadata.page)
        doc_map[fn]["chunks"] += 1

    return [
        DocumentInfo(
            filename=data["filename"],
            document_id=data["document_id"],
            total_pages=len(data["pages"]),
            total_chunks=data["chunks"],
        )
        for data in doc_map.values()
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentInfo])
def documents():
    return list_documents()


@app.post("/ingest")
def ingest_endpoint(recreate: bool = False):
    from src.indexing import ingest
    count = ingest(recreate=recreate)
    return {"status": "ok", "chunks_indexed": count}


@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    res = save_and_ingest_pdf(content, file.filename or "uploaded.pdf")
    return UploadResponse(
        filename=res["filename"], chunks_indexed=res["chunks_indexed"]
    )


@app.post("/ask", response_model=RagAnswer)
def ask_endpoint(req: AskRequest):
    return answer(req.question, k=req.k, filters=filters_to_dict(req.filters))


@app.post("/summarize", response_model=Summary)
def summarize_endpoint(req: SummarizeRequest):
    return summarize(
        document=req.document,
        query=req.query,
        filters=filters_to_dict(req.filters),
        k=req.k,
    )


@app.post("/quiz", response_model=QuizSet)
def quiz_endpoint(req: QuizRequest):
    return generate_quiz(
        document=req.document,
        query=req.query,
        filters=filters_to_dict(req.filters),
        count=req.count,
        k=req.k,
    )


@app.post("/flashcards", response_model=FlashcardSet)
def flashcards_endpoint(req: FlashcardsRequest):
    return generate_flashcards(
        document=req.document,
        query=req.query,
        filters=filters_to_dict(req.filters),
        count=req.count,
        k=req.k,
    )
