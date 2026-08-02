from __future__ import annotations

import hashlib
import posixpath
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit, urlunsplit

from .errors import InvalidIntelligenceInput

_CNBLOGS_ARTICLE = re.compile(r"^/[A-Za-z0-9._-]+/(?:p|articles)/[A-Za-z0-9._-]+(?:\.html)?$")


@dataclass(frozen=True)
class SourceAddress:
    source_url: str
    normalized_url: str
    host: str


class SourceAdapterRegistry:
    supported_hosts = {"cnblogs.com", "www.cnblogs.com"}
    canonical_host = "www.cnblogs.com"

    def normalize(self, value: str) -> SourceAddress:
        raw = value.strip()
        try:
            parsed = urlsplit(raw)
            port = parsed.port
        except ValueError as exc:
            raise InvalidIntelligenceInput("invalid_url", "来源 URL 格式无效") from exc
        if parsed.scheme.lower() not in {"http", "https"}:
            raise InvalidIntelligenceInput("unsupported_protocol", "只支持公开 HTTP(S) 来源")
        if parsed.username is not None or parsed.password is not None:
            raise InvalidIntelligenceInput("url_credentials_forbidden", "来源 URL 不能包含用户名或凭据")
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        if not host:
            raise InvalidIntelligenceInput("invalid_url", "来源 URL 缺少有效主机")
        if port is not None and port not in {80, 443}:
            raise InvalidIntelligenceInput("unsupported_port", "来源 URL 只允许默认 HTTP(S) 端口")
        if host not in self.supported_hosts:
            raise InvalidIntelligenceInput(
                "source_not_supported",
                "当前只支持博客园公开文章链接；其他来源请直接补充正文",
            )

        decoded_path = unquote(parsed.path or "/")
        normalized_path = posixpath.normpath(decoded_path)
        if not normalized_path.startswith("/"):
            normalized_path = f"/{normalized_path}"
        normalized_path = normalized_path.rstrip("/") or "/"
        if not _CNBLOGS_ARTICLE.fullmatch(normalized_path):
            raise InvalidIntelligenceInput(
                "source_path_not_supported",
                "该博客园链接不是受支持的公开文章路径，请补充正文",
            )

        normalized_url = urlunsplit(("https", self.canonical_host, normalized_path, "", ""))
        return SourceAddress(source_url=normalized_url, normalized_url=normalized_url, host=self.canonical_host)

    def validate_redirect(self, value: str) -> SourceAddress:
        return self.normalize(value)


def url_fingerprint(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
