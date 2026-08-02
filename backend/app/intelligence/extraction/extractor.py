from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

SCHEMA_VERSION = "interview-extraction.v1"
PROCESSOR_VERSION = "deterministic-lines.v1"

BLOCK_TYPES = {
    "question",
    "author_answer",
    "interviewer_feedback",
    "follow_up",
    "process_description",
    "unknown",
}

_ROUND_HEADER = re.compile(
    r"^(?:第?[一二三四五六七八九十0-9]+\s*(?:轮|面)|(?:HR|hr|技术|主管|总监|业务)面)(?:\s*[:：\-—].*)?$"
)
_FOLLOW_UP = re.compile(r"^(?:追问|继续问|又问|follow\s*[- ]?up)\s*[:：\-—]?\s*", re.IGNORECASE)
_ANSWER = re.compile(r"^(?:A|答|回答|我的回答|我答)\s*[:：\-—]\s*", re.IGNORECASE)
_FEEDBACK = re.compile(r"^(?:面试官(?:反馈|评价|说)|反馈|评价)\s*[:：\-—]?\s*")
_QUESTION = re.compile(r"^(?:Q|问|问题|面试官问)\s*[:：\-—]\s*", re.IGNORECASE)
_PROCESS = re.compile(r"^(?:面试流程|流程|自我介绍|首先|然后|接着|最后|面试(?:持续|开始|结束)|全程)")
_TOPICS = ("Java", "JVM", "Spring", "Redis", "MySQL", "PostgreSQL", "数据库", "索引", "线程", "网络", "TCP", "HTTP", "消息队列", "算法", "项目")


@dataclass(frozen=True)
class RoundMark:
    ordinal: int
    label: str | None
    start_char: int
    end_char: int


@dataclass(frozen=True)
class ChunkMark:
    ordinal: int
    round_ordinal: int | None
    block_type: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
class CandidateMark:
    chunk_ordinal: int
    round_ordinal: int | None
    candidate_key: str
    field_kind: str
    extracted_text: str
    topic_candidate: str | None
    start_char: int
    end_char: int


@dataclass(frozen=True)
class ExtractionResult:
    rounds: tuple[RoundMark, ...]
    chunks: tuple[ChunkMark, ...]
    candidates: tuple[CandidateMark, ...]


def input_fingerprint(content_hash: str, cleaning_version: str) -> str:
    source = f"{content_hash}:{cleaning_version}:{SCHEMA_VERSION}:{PROCESSOR_VERSION}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def extract_document(cleaned_content: str, content_hash: str) -> ExtractionResult:
    if not cleaned_content.strip():
        raise ValueError("cleaned_content is empty")

    raw_lines = list(re.finditer(r"[^\n]+", cleaned_content))
    nonempty = [(match.start(), match.end(), match.group(0)) for match in raw_lines if match.group(0).strip()]
    round_headers: list[tuple[int, int, str]] = []
    for start, end, raw in nonempty:
        label = raw.strip()
        if _ROUND_HEADER.fullmatch(label):
            round_headers.append((start, end, label))

    rounds = tuple(
        RoundMark(
            ordinal=index + 1,
            label=label,
            start_char=start,
            end_char=round_headers[index + 1][0] if index + 1 < len(round_headers) else len(cleaned_content),
        )
        for index, (start, _end, label) in enumerate(round_headers)
    )

    chunks: list[ChunkMark] = []
    candidates: list[CandidateMark] = []
    current_round: int | None = None
    round_by_start = {item.start_char: item.ordinal for item in rounds}

    for start, end, raw in nonempty:
        stripped = raw.strip()
        left_trim = len(raw) - len(raw.lstrip())
        block_start = start + left_trim
        block_end = block_start + len(stripped)
        if block_start in round_by_start:
            current_round = round_by_start[block_start]
        block_type, extracted, relative_start = _classify(stripped)
        ordinal = len(chunks) + 1
        chunks.append(ChunkMark(ordinal, current_round, block_type, block_start, block_end))

        if block_type in {"question", "follow_up"} and extracted:
            extracted = extracted[:4000]
            candidate_start = block_start + relative_start
            candidate_end = candidate_start + len(extracted)
            kind = "follow_up" if block_type == "follow_up" else "question"
            key_source = f"{content_hash}:{kind}:{candidate_start}:{candidate_end}:{extracted}"
            candidates.append(CandidateMark(
                chunk_ordinal=ordinal,
                round_ordinal=current_round,
                candidate_key=hashlib.sha256(key_source.encode("utf-8")).hexdigest(),
                field_kind=kind,
                extracted_text=extracted,
                topic_candidate=_topic_candidate(extracted),
                start_char=candidate_start,
                end_char=candidate_end,
            ))

    return ExtractionResult(tuple(rounds), tuple(chunks), tuple(candidates))


def _classify(text: str) -> tuple[str, str | None, int]:
    if _ROUND_HEADER.fullmatch(text):
        return "process_description", None, 0
    for block_type, pattern in (
        ("follow_up", _FOLLOW_UP),
        ("author_answer", _ANSWER),
        ("interviewer_feedback", _FEEDBACK),
        ("question", _QUESTION),
    ):
        match = pattern.match(text)
        if match:
            extracted = text[match.end():].strip()
            relative = match.end() + (len(text[match.end():]) - len(text[match.end():].lstrip()))
            return block_type, extracted if block_type in {"question", "follow_up"} else None, relative
    if text.endswith(("?", "？")):
        return "question", text, 0
    if _PROCESS.match(text):
        return "process_description", None, 0
    return "unknown", None, 0


def _topic_candidate(text: str) -> str | None:
    matches = [topic for topic in _TOPICS if topic.casefold() in text.casefold()]
    return " / ".join(matches[:3]) or None
