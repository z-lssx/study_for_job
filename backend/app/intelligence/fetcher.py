from __future__ import annotations

import ipaddress
import socket
import urllib.robotparser
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlsplit

import httpx

from .errors import IntelligenceError
from .sources import SourceAdapterRegistry

USER_AGENT = "study-for-job/0.1 (local personal interview research)"
MAX_ROBOTS_BYTES = 64 * 1024
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3


@dataclass(frozen=True)
class FetchedContent:
    raw_content: str
    media_type: str
    final_url: str


@dataclass(frozen=True)
class _ResponseContent:
    text: str
    media_type: str
    final_url: str
    headers: httpx.Headers


class SafePublicFetcher:
    def __init__(
        self,
        adapters: SourceAdapterRegistry | None = None,
        resolver: Callable[..., list[tuple]] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.adapters = adapters or SourceAdapterRegistry()
        self.resolver = resolver or socket.getaddrinfo
        self.transport = transport

    def fetch(self, normalized_url: str) -> FetchedContent:
        address = self.adapters.normalize(normalized_url)
        timeout = httpx.Timeout(connect=5.0, read=12.0, write=5.0, pool=5.0)
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"}
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=False, transport=self.transport) as client:
            robots_url = f"https://{address.host}/robots.txt"
            robots = self._read(client, robots_url, MAX_ROBOTS_BYTES, {"text/plain"}, purpose="robots")
            self._assert_robots_allows(robots.text, address.normalized_url)
            page = self._read(
                client,
                address.normalized_url,
                MAX_PAGE_BYTES,
                {"text/html", "text/plain"},
                purpose="article",
            )

        robots_header = page.headers.get("x-robots-tag", "").lower()
        if "noindex" in robots_header or "none" in robots_header:
            raise IntelligenceError("source_disallowed", "来源页面明确限制自动处理，请补充正文", False)
        return FetchedContent(page.text, page.media_type, page.final_url)

    def _read(
        self,
        client: httpx.Client,
        initial_url: str,
        maximum_bytes: int,
        allowed_media_types: set[str],
        purpose: str,
    ) -> _ResponseContent:
        current_url = initial_url
        for redirect_count in range(MAX_REDIRECTS + 1):
            parsed = urlsplit(current_url)
            self._assert_supported_target(current_url, purpose)
            self._assert_public_dns(parsed.hostname or "", parsed.port or 443)
            try:
                with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count >= MAX_REDIRECTS:
                            raise IntelligenceError("redirect_limit_exceeded", "来源重定向次数过多，请补充正文", False)
                        location = response.headers.get("location", "").strip()
                        if not location:
                            raise IntelligenceError("redirect_invalid", "来源返回了无效重定向，请补充正文", False)
                        current_url = urljoin(current_url, location)
                        continue
                    self._assert_status(response.status_code, purpose)
                    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if media_type not in allowed_media_types:
                        code = "source_policy_unavailable" if purpose == "robots" else "unsupported_content_type"
                        message = "无法确认来源抓取许可，请补充正文" if purpose == "robots" else "来源不是可处理的 HTML 或纯文本，请补充正文"
                        raise IntelligenceError(code, message, False)
                    content_length = response.headers.get("content-length")
                    if content_length and content_length.isdigit() and int(content_length) > maximum_bytes:
                        raise IntelligenceError("content_too_large", "来源内容超过安全处理上限，请补充正文", False)
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > maximum_bytes:
                            raise IntelligenceError("content_too_large", "来源内容超过安全处理上限，请补充正文", False)
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    encoding = response.encoding or "utf-8"
                    return _ResponseContent(
                        text=raw.decode(encoding, errors="replace"),
                        media_type=media_type,
                        final_url=current_url,
                        headers=response.headers,
                    )
            except IntelligenceError:
                raise
            except httpx.TimeoutException as exc:
                raise IntelligenceError("network_timeout", "来源响应超时，系统将按退避策略重试", True) from exc
            except (httpx.ConnectError, httpx.NetworkError, httpx.ProtocolError) as exc:
                raise IntelligenceError("network_unavailable", "暂时无法连接公开来源，系统将按退避策略重试", True) from exc
            except httpx.HTTPError as exc:
                raise IntelligenceError("network_unavailable", "公开来源请求失败，系统将按退避策略重试", True) from exc
        raise IntelligenceError("redirect_limit_exceeded", "来源重定向次数过多，请补充正文", False)

    def _assert_supported_target(self, value: str, purpose: str) -> None:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or parsed.username is not None or parsed.password is not None:
            raise IntelligenceError("redirect_not_allowed", "来源重定向越过安全边界，请补充正文", False)
        host = (parsed.hostname or "").lower().rstrip(".")
        if host not in self.adapters.supported_hosts:
            raise IntelligenceError("redirect_not_allowed", "来源重定向到不受支持的主机，请补充正文", False)
        if parsed.port is not None and parsed.port not in {80, 443}:
            raise IntelligenceError("redirect_not_allowed", "来源重定向到非默认端口，请补充正文", False)
        if purpose == "robots":
            if parsed.path.rstrip("/") != "/robots.txt" or parsed.query:
                raise IntelligenceError("source_policy_unavailable", "无法确认来源抓取许可，请补充正文", False)
        else:
            try:
                self.adapters.validate_redirect(value)
            except IntelligenceError as exc:
                raise IntelligenceError("redirect_not_allowed", "来源重定向越过支持范围，请补充正文", False) from exc

    def _assert_public_dns(self, host: str, port: int) -> None:
        try:
            addresses = self.resolver(host, port, type=socket.SOCK_STREAM)
        except (socket.gaierror, OSError) as exc:
            raise IntelligenceError("dns_unavailable", "来源域名暂时无法解析，系统将按退避策略重试", True) from exc
        if not addresses:
            raise IntelligenceError("dns_unavailable", "来源域名暂时无法解析，系统将按退避策略重试", True)
        for address in addresses:
            raw_ip = address[4][0]
            try:
                parsed_ip = ipaddress.ip_address(raw_ip)
            except ValueError as exc:
                raise IntelligenceError("unsafe_network_target", "来源解析结果不在公共网络范围", False) from exc
            if not parsed_ip.is_global:
                raise IntelligenceError("unsafe_network_target", "来源解析到私网、本机或保留地址，已拒绝处理", False)

    @staticmethod
    def _assert_status(status_code: int, purpose: str) -> None:
        if status_code == 200:
            return
        if purpose == "robots":
            if status_code == 429 or 500 <= status_code <= 599:
                raise IntelligenceError("source_policy_unavailable", "暂时无法确认来源抓取许可，系统将重试", True)
            raise IntelligenceError("source_policy_unavailable", "来源抓取许可不明确，请补充正文", False)
        if status_code == 429:
            raise IntelligenceError("upstream_rate_limited", "来源当前限流，系统将按退避策略重试", True)
        if 500 <= status_code <= 599:
            raise IntelligenceError("upstream_temporary", "来源服务暂时不可用，系统将按退避策略重试", True)
        if status_code in {401, 403}:
            raise IntelligenceError("source_access_restricted", "来源需要权限或拒绝访问，请补充正文", False)
        raise IntelligenceError("upstream_http_error", "来源返回不可处理的响应，请补充正文", False)

    @staticmethod
    def _assert_robots_allows(robots_text: str, target_url: str) -> None:
        meaningful = [line.strip() for line in robots_text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        if not any(line.lower().startswith("user-agent:") for line in meaningful):
            raise IntelligenceError("source_policy_unavailable", "来源抓取许可不明确，请补充正文", False)
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(urljoin(target_url, "/robots.txt"))
        parser.parse(robots_text.splitlines())
        if not parser.can_fetch(USER_AGENT, target_url):
            raise IntelligenceError("source_disallowed", "来源规则不允许自动处理该页面，请补充正文", False)
