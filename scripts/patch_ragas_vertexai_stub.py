"""One-time environment fix, run once after `pip install -r requirements.txt`:
    python scripts/patch_ragas_vertexai_stub.py

ragas 0.2.6's `ragas/llms/base.py` unconditionally imports
`ChatVertexAI` from `langchain_community.chat_models.vertexai` at module load
time. Current langchain-community releases removed that submodule (Vertex AI
support moved to the standalone langchain-google-vertexai package), so a
plain `import ragas` fails with:

    ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'

This project never uses Vertex AI (only OpenAI-family models via OpenRouter),
so the fix is a placeholder module at the exact import path ragas expects,
not a real integration. This has to live inside site-packages (not import
hooks or sys.path tricks) because ragas imports the submodule by dotted path
before any of our own code runs.
"""

from pathlib import Path

import langchain_community

STUB_CONTENT = '''"""Compatibility stub — see scripts/patch_ragas_vertexai_stub.py."""


class ChatVertexAI:  # pragma: no cover - intentionally unused placeholder
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "ChatVertexAI is a compatibility stub. This project does not use Vertex AI."
        )
'''


def main() -> None:
    target = Path(langchain_community.__file__).parent / "chat_models" / "vertexai.py"
    if target.exists():
        print(f"Already present: {target}")
        return
    target.write_text(STUB_CONTENT, encoding="utf-8")
    print(f"Wrote stub module: {target}")


if __name__ == "__main__":
    main()
