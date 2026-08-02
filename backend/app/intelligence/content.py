from __future__ import annotations

import hashlib
import re
import unicodedata
from html.parser import HTMLParser

from .errors import InvalidIntelligenceInput, IntelligenceError

CLEANING_VERSION = "plain-text-v1"
MIN_MANUAL_TEXT_LENGTH = 20
MIN_FETCHED_TEXT_LENGTH = 80
MAX_CLEANED_TEXT_LENGTH = 500_000

_WHITESPACE = re.compile(r"[\t\f\v \u00a0\u3000]+")
_FOCUS_MARKERS = ("cnblogs_post_body", "post-body", "post_body", "blogpost-body", "article-body", "article-content")
_BLOCK_TAGS = {
    "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figcaption", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "main", "ol", "p", "pre", "section",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
_IGNORED_TAGS = {"button", "canvas", "footer", "form", "header", "iframe", "nav", "noscript", "script", "style", "svg"}


def normalize_plain_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    previous_blank = True
    for raw_line in normalized.split("\n"):
        line = _WHITESPACE.sub(" ", raw_line).strip()
        if not line:
            if not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(line)
        previous_blank = False
    cleaned = "\n".join(lines).strip()
    return cleaned[:MAX_CLEANED_TEXT_LENGTH]


def content_hash(cleaned_content: str) -> str:
    return hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()


def validate_manual_content(value: str) -> tuple[str, str]:
    cleaned = normalize_plain_text(value)
    if len(cleaned) < MIN_MANUAL_TEXT_LENGTH:
        raise InvalidIntelligenceInput("content_too_short", f"面经正文至少需要 {MIN_MANUAL_TEXT_LENGTH} 个有效字符")
    return cleaned, content_hash(cleaned)


class _ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[bool, bool, str]] = []
        self.visible: list[str] = []
        self.focused: list[str] = []
        self.title_parts: list[str] = []
        self.heading_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        parent_ignored = self._stack[-1][0] if self._stack else False
        parent_focused = self._stack[-1][1] if self._stack else False
        attr_text = " ".join(value or "" for key, value in attrs if key in {"id", "class", "role"}).lower()
        ignored = parent_ignored or tag in _IGNORED_TAGS
        focused = parent_focused or tag in {"article", "main"} or any(marker in attr_text for marker in _FOCUS_MARKERS)
        self._stack.append((ignored, focused, tag))
        if tag in _BLOCK_TAGS and not ignored:
            self._append_break(focused)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return
        ignored, focused, _opened = self._stack.pop()
        if tag in _BLOCK_TAGS and not ignored:
            self._append_break(focused)

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        ignored, focused, tag = self._stack[-1]
        if ignored:
            return
        self.visible.append(data)
        if focused:
            self.focused.append(data)
        if tag == "title":
            self.title_parts.append(data)
        elif tag == "h1":
            self.heading_parts.append(data)

    def _append_break(self, focused: bool) -> None:
        self.visible.append("\n")
        if focused:
            self.focused.append("\n")


def clean_html(raw_html: str) -> tuple[str | None, str]:
    parser = _ArticleTextParser()
    try:
        parser.feed(raw_html)
        parser.close()
    except Exception as exc:
        raise IntelligenceError("parse_failed", "页面正文解析失败，可补充正文后重新处理", False) from exc

    focused = normalize_plain_text("".join(parser.focused))
    visible = normalize_plain_text("".join(parser.visible))
    cleaned = focused if len(focused) >= MIN_FETCHED_TEXT_LENGTH else visible
    if len(cleaned) < MIN_FETCHED_TEXT_LENGTH:
        raise IntelligenceError("content_too_short", "页面没有足够的有效面经正文，可补充正文后重新处理", False)
    title = normalize_plain_text(" ".join(parser.heading_parts)) or normalize_plain_text(" ".join(parser.title_parts))
    return (title[:300] or None), cleaned
