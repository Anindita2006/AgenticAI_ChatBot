"""Shared DeepEval judge model for every governance test suite in this
directory: deepeval's built-in `OpenRouterModel` pointed at this project's
own OpenRouter key/base URL and JUDGE_MODEL (openai/gpt-4o) -- the same
larger, separate-from-the-chatbot-under-test model `eval/judge.py` already
uses, for the same reason (avoid the chatbot judging itself).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from deepeval.models import OpenRouterModel

import config


def get_judge_model() -> OpenRouterModel:
    return OpenRouterModel(
        model=config.JUDGE_MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        temperature=0,
    )
