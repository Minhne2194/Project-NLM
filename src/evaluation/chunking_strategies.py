from dataclasses import dataclass
from typing import Any, Callable

from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.store import get_embeddings

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass
class ChunkingConfig:
    name: str
    chunker_fn: Callable[[], Any]


def get_recursive_chunker(chunk_size: int, chunk_overlap: int):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=DEFAULT_SEPARATORS,
        keep_separator=False,
    )


def get_semantic_chunker(breakpoint_threshold_type: str = "interquartile"):
    embeddings = get_embeddings()
    return SemanticChunker(
        embeddings,
        breakpoint_threshold_type=breakpoint_threshold_type,
    )


RECURSIVE_CONFIGS = [
    ChunkingConfig("recursive_500_50", lambda: get_recursive_chunker(500, 50)),
    ChunkingConfig("recursive_800_100", lambda: get_recursive_chunker(800, 100)),
    ChunkingConfig("recursive_1000_150", lambda: get_recursive_chunker(1000, 150)),
    ChunkingConfig("recursive_1500_200", lambda: get_recursive_chunker(1500, 200)),
]

SEMANTIC_CONFIGS = [
    ChunkingConfig("semantic_interquartile", lambda: get_semantic_chunker("interquartile")),
    ChunkingConfig("semantic_std_dev", lambda: get_semantic_chunker("standard_deviation")),
    ChunkingConfig("semantic_percentile", lambda: get_semantic_chunker("percentile")),
]
