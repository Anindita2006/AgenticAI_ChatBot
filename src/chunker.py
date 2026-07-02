"""A dependency-free recursive character text splitter (same algorithm shape as
LangChain's RecursiveCharacterTextSplitter): try the coarsest separator first
(paragraph breaks), fall back to finer ones (line, sentence, word) only for
pieces that are still too big, then stitch adjacent chunks back together with
a fixed character overlap so context isn't lost at a chunk boundary.
"""

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split_on_separator(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    if not separators:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep, rest = separators[0], separators[1:]
    if sep not in text:
        return _split_on_separator(text, chunk_size, rest)

    parts = text.split(sep)
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current}{sep}{part}" if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size:
                chunks.extend(_split_on_separator(part, chunk_size, rest))
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)
    return chunks


def recursive_character_split(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    separators: list[str] | None = None,
) -> list[str]:
    raw_chunks = _split_on_separator(text, chunk_size, separators or DEFAULT_SEPARATORS)

    if chunk_overlap <= 0 or len(raw_chunks) <= 1:
        return raw_chunks

    overlapped = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        prev = raw_chunks[i - 1]
        tail = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
        # Snap to a word boundary so overlap never starts mid-word (e.g. "ge/Management").
        space_idx = tail.find(" ")
        if 0 < space_idx < len(tail) - 1:
            tail = tail[space_idx + 1:]
        overlapped.append(f"{tail} {raw_chunks[i]}".strip())
    return overlapped
