"""Phase 2 — Retrieval.

Wraps the persisted ChromaDB collection with a single retrieve() call: embed
the query with the same model used at ingestion time, run a top-k similarity
search, and optionally scope the search to one section via metadata filtering.

Run directly to smoke-test retrieval in isolation (no generation involved):
    python src/retriever.py
"""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chromadb

import config


@dataclass
class RetrievedChunk:
    text: str
    source: str
    section: str
    page: int
    distance: float


def _get_collection():
    client = chromadb.PersistentClient(path=str(config.VECTORSTORE_DIR))
    return client.get_collection(config.COLLECTION_NAME)


def list_sections() -> list[str]:
    """All distinct section names currently in the index, for the UI's filter dropdown."""
    collection = _get_collection()
    metadatas = collection.get(include=["metadatas"])["metadatas"]
    return sorted({m["section"] for m in metadatas})


def get_index_stats() -> dict:
    """Chunk count and the chunking config actually used to build the index
    (read from collection metadata, not from the current config.py defaults —
    those can drift apart if the index hasn't been rebuilt since a config change).
    """
    collection = _get_collection()
    meta = collection.metadata or {}
    return {
        "chunk_count": collection.count(),
        "chunk_size": meta.get("chunk_size"),
        "chunk_overlap": meta.get("chunk_overlap"),
    }


def retrieve(query: str, top_k: int = config.DEFAULT_TOP_K, section: str | None = None) -> list[RetrievedChunk]:
    if not query.strip():
        return []

    embed_client = config.get_embedding_client()
    query_embedding = embed_client.embeddings.create(
        model=config.EMBEDDING_MODEL, input=[query]
    ).data[0].embedding

    collection = _get_collection()
    where = {"section": section} if section else None
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        chunks.append(RetrievedChunk(
            text=doc,
            source=meta["source"],
            section=meta["section"],
            page=meta["page"],
            distance=dist,
        ))
    return chunks


if __name__ == "__main__":
    test_queries = [
        "What is the tuition fee for CSE?",
        "What are the top recruiters at BVRIT Hyderabad?",
        "Does BVRIT Hyderabad accept JEE Main scores for admission?",
    ]

    print(f"Sections in index: {list_sections()}\n")

    for q in test_queries:
        print(f"QUERY: {q}")
        results = retrieve(q, top_k=config.DEFAULT_TOP_K)
        for r in results:
            print(f"  [dist={r.distance:.4f}] ({r.section}, page {r.page}) {r.text[:90]!r}")
        print()
