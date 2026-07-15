"""Prompt Registry — centralized prompt template management.

Usage:
    from app.prompts import prompt

    # Single message
    user_msg = prompt("explain_sql", sql="SELECT * FROM data")

    # System + user message pair
    sys_msg, user_msg = prompt("sql", table_schema=..., question=...)
"""

import os
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent
_cache: dict[str, str] = {}


def _load(name: str) -> str:
    if name not in _cache:
        path = _PROMPTS_DIR / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            _cache[name] = f.read()
    return _cache[name]


def prompt(name: str, **kwargs) -> str | tuple[str, str]:
    """Render a prompt template.

    Templates can use {variable} placeholders.

    Multi-message templates separate system and user with a ``---`` line:
        You are a SQL expert.
        ---
        Table: {table_schema}
        Question: {question}

    Single-message templates just return the rendered string.
    """
    template = _load(name)

    if "\n---\n" in template:
        parts = template.split("\n---\n", 1)
        return parts[0].format(**kwargs).strip(), parts[1].format(**kwargs).strip()

    return template.format(**kwargs).strip()


class PromptManager:
    """Programmatic interface for prompt management (future: versioning, A/B test)."""

    def __init__(self, prompts_dir: str | None = None):
        self._dir = Path(prompts_dir) if prompts_dir else _PROMPTS_DIR

    def render(self, name: str, **kwargs) -> str | tuple[str, str]:
        return prompt(name, **kwargs)

    def list_templates(self) -> list[str]:
        return sorted([p.stem for p in self._dir.glob("*.txt")])
