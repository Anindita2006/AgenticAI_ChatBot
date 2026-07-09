"""Central configuration: paths, chunking defaults, and LLM/embedding clients.

All model access goes through OpenRouter by default (one API key, OpenAI-compatible
surface). Embeddings have their own base_url/key override because not all
OpenRouter accounts have embedding-model access — set EMBEDDING_BASE_URL /
EMBEDDING_API_KEY to point at OpenAI directly if needed, without touching the
rest of the config.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Test cases and document content include non-Latin script (Telugu/Hindi robustness
# cases, em-dashes). Windows consoles often default to cp1252, which raises
# UnicodeEncodeError on those rather than degrading gracefully — force UTF-8 output.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VECTORSTORE_DIR = PROJECT_ROOT / "vectorstore"
EVAL_DIR = PROJECT_ROOT / "eval"

KB_PDF_PATH = DATA_DIR / "knowledge_base.pdf"
KB_SOURCE_NAME = "knowledge_base.pdf"

COLLECTION_NAME = "bvrit_college_info"

# Chunking defaults — see spec.md "Chunking strategy" for the justification.
# 400/60 was chosen empirically over an initial 800/120: sections are short,
# fact-dense paragraphs, and 800-char chunks were merging distinct facts (e.g.
# admission categories + JEE policy) into one embedding, diluting retrieval
# precision for pointed questions. 400/60 keeps each chunk closer to one fact.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "60"))

DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "6"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
# Explicit cap, not the model's default max output (16384 for gpt-4o-mini): an
# uncapped request has to be affordable at its full requested size even though a
# cited FAQ answer never needs anywhere near that much, which caused spurious
# "insufficient credits" 402s when the account balance was merely low, not empty.
MAX_ANSWER_TOKENS = int(os.getenv("MAX_ANSWER_TOKENS", "1500"))
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-4o")
TEST_GEN_MODEL = os.getenv("TEST_GEN_MODEL", "openai/gpt-4o")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "") or OPENROUTER_API_KEY
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "") or OPENROUTER_BASE_URL

PERFORMANCE_SLA_SECONDS = float(os.getenv("PERFORMANCE_SLA_SECONDS", "10"))


def get_chat_client() -> OpenAI:
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


def get_embedding_client() -> OpenAI:
    if not EMBEDDING_API_KEY:
        raise RuntimeError(
            "EMBEDDING_API_KEY / OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return OpenAI(api_key=EMBEDDING_API_KEY, base_url=EMBEDDING_BASE_URL)
