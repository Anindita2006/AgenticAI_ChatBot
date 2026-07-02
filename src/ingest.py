"""Phase 1 — Ingest and index.

Loads the .docx knowledge base, splits it into chunks that respect the
document's section headings, embeds each chunk, and persists everything to a
local ChromaDB collection with metadata (source, section, page, chunk_index)
so retrieval can cite and filter by section later.

Run directly to (re)build the index:
    python src/ingest.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chromadb

import config
from chunker import recursive_character_split
from loader import load_docx_sections

DOCUMENT_TITLE = "BVRIT Hyderabad College of Engineering for Women"


def _embed_batch(texts: list[str]) -> list[list[float]]:
    client = config.get_embedding_client()
    response = client.embeddings.create(model=config.EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def build_chunks(docx_path=config.KB_DOCX_PATH) -> list[dict]:
    """Each chunk keeps two forms of its text: `text` (the clean original,
    used for citations and as LLM context) and `embed_text` (the same text
    prefixed with the document title + section name). Splitting a section into
    several chunks means most chunks lose the sentence that establishes *which*
    college/section they're about — a mid-section chunk like "Top recruiters
    include Microsoft, Amazon..." has no lexical/semantic anchor back to "BVRIT
    Hyderabad" or "Placements" on its own. Embedding the prefixed version fixes
    that without polluting what's actually shown to the user or the LLM.
    """
    sections = load_docx_sections(docx_path)
    chunks = []
    for section in sections:
        pieces = recursive_character_split(
            section.text,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
        for i, piece in enumerate(pieces):
            chunks.append({
                "id": f"{section.page}-{section.section[:30]}-{i}".replace(" ", "_"),
                "text": piece,
                "embed_text": f"{DOCUMENT_TITLE} — {section.section}: {piece}",
                "metadata": {
                    "source": config.KB_SOURCE_NAME,
                    "section": section.section,
                    "page": section.page,
                    "chunk_index": i,
                },
            })
    return chunks


def ingest(docx_path=config.KB_DOCX_PATH, persist_dir=config.VECTORSTORE_DIR) -> int:
    chunks = build_chunks(docx_path)
    if not chunks:
        raise RuntimeError(f"No chunks produced from {docx_path} — check the document.")

    texts = [c["text"] for c in chunks]
    embeddings = _embed_batch([c["embed_text"] for c in chunks])

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    client.delete_collection(config.COLLECTION_NAME) if config.COLLECTION_NAME in [
        c.name for c in client.list_collections()
    ] else None
    collection = client.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"chunk_size": config.CHUNK_SIZE, "chunk_overlap": config.CHUNK_OVERLAP},
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[c["metadata"] for c in chunks],
    )

    return collection.count()


def verify_persistence(persist_dir=config.VECTORSTORE_DIR) -> int:
    """Reload the store from disk (fresh client) and return its chunk count."""
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_collection(config.COLLECTION_NAME)
    return collection.count()


if __name__ == "__main__":
    count = ingest()
    print(f"Indexed {count} chunks into '{config.COLLECTION_NAME}' at {config.VECTORSTORE_DIR}")
    print(f"chunk_size={config.CHUNK_SIZE}, chunk_overlap={config.CHUNK_OVERLAP}")

    reloaded_count = verify_persistence()
    status = "OK" if reloaded_count == count else "MISMATCH"
    print(f"Persistence check: reloaded collection has {reloaded_count} chunks [{status}]")
