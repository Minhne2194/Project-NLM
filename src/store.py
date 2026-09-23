from functools import lru_cache
from typing import Generator

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.config import settings

INDEXED_PAYLOAD_FIELDS = {
    "metadata.document_id": qmodels.PayloadSchemaType.KEYWORD,
    "metadata.filename": qmodels.PayloadSchemaType.KEYWORD,
    "metadata.page": qmodels.PayloadSchemaType.INTEGER,
}


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    device = "cpu" if settings.hf_device == -1 else f"cuda:{settings.hf_device}"
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.storage_dir))


def get_vector_store(collection_name: str | None = None) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_client(),
        collection_name=collection_name or settings.qdrant_collection,
        embedding=get_embeddings(),
    )


def ensure_collection(recreate: bool = False, collection_name: str | None = None) -> None:
    client = get_client()
    name = collection_name or settings.qdrant_collection
    exists = client.collection_exists(name)

    if exists and recreate:
        client.delete_collection(name)
        exists = False

    if not exists:
        dim = len(get_embeddings().embed_query("dimension probe"))
        client.create_collection(
            collection_name=name,
            vectors_config=qmodels.VectorParams(
                size=dim, distance=qmodels.Distance.COSINE
            ),
        )

    payload_schema = client.get_collection(name).payload_schema or {}
    for field, schema in INDEXED_PAYLOAD_FIELDS.items():
        if payload_schema.get(field) is None:
            client.create_payload_index(name, field_name=field, field_schema=schema)


def scroll_all(
    collection_name: str | None = None,
    scroll_filter: qmodels.Filter | None = None,
    batch_size: int = 64,
) -> Generator[list, None, None]:
    client = get_client()
    name = collection_name or settings.qdrant_collection
    if not client.collection_exists(name):
        return

    offset = None
    while True:
        records, next_offset = client.scroll(
            collection_name=name,
            scroll_filter=scroll_filter,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            break
        yield records
        if next_offset is None:
            break
        offset = next_offset
