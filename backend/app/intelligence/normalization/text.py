from __future__ import annotations

import hashlib
import re
import unicodedata
from uuid import UUID

_LEADING_NUMBER = re.compile(r"^\s*(?:第?\d+[.、)]|[（(]\d+[）)])\s*")
_WHITESPACE = re.compile(r"\s+")
_TRAILING_PROMPT_PUNCTUATION = "?？!！。．.；;：:，,、"


def normalize_question_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = _LEADING_NUMBER.sub("", normalized)
    normalized = _WHITESPACE.sub(" ", normalized)
    normalized = normalized.rstrip(_TRAILING_PROMPT_PUNCTUATION).strip()
    if not normalized:
        raise ValueError("question text is empty after normalization")
    return normalized


def question_normalization_key(value: str) -> str:
    normalized = normalize_question_text(value).casefold().replace(" ", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def occurrence_key(document_id: UUID, round_ordinal: int | None, normalization_key: str) -> str:
    scope = f"{document_id}:{round_ordinal or 0}:{normalization_key}"
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()
