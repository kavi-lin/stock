"""Fetch short original-page passages only for promoted events (zero LLM)."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from scripts.nexus.source_packets import _page_passages
from scripts.research.store import digest, now_iso


def public_url(url):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("unsupported evidence URL")
    addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("evidence URL must resolve to a public host")
    return url


def page(url, terms):
    url = public_url(url)
    for _ in range(4):
        with requests.get(url, timeout=12, allow_redirects=False, stream=True,
                          headers={"User-Agent": "AIC-Research/1.0 (public source research)"}) as response:
            if response.is_redirect:
                url = public_url(urljoin(url, response.headers["Location"]))
                continue
            response.raise_for_status()
            if "html" not in response.headers.get("Content-Type", "").lower():
                return {"status": "unsupported_content", "url": url, "excerpts": []}
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 2_000_000:
                    return {"status": "too_large", "url": url, "excerpts": []}
                chunks.append(chunk)
            html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
            content, excerpts = _page_passages(html, terms)
            attachments = []
            if urlsplit(url).hostname in {"www.sec.gov", "sec.gov"} and url.endswith("-index.html"):
                soup = BeautifulSoup(html, "html.parser")
                for row in soup.select("table.tableFile tr"):
                    cells = row.find_all("td")
                    if len(cells) >= 4 and cells[3].get_text(strip=True) in {"8-K", "6-K", "EX-99.1", "EX-99.2"}:
                        link = cells[2].find("a", href=True)
                        if link:
                            attachments.append(urljoin(url, link["href"]))
            return {"status": "fetched" if excerpts else "no_relevant_excerpt", "url": url,
                    "excerpts": excerpts[:3], "content_hash": digest(content),
                    "attachments": attachments[:2]}
    return {"status": "redirect_limit", "url": url, "excerpts": []}


def enrich(event, fetch=page):
    terms = [event["headline"], *event["tickers"], "revenue", "guidance", "results"]
    health, evidence = [], list(event["evidence"])
    urls = [event["url"]]
    for url in urls:
        try:
            result = fetch(url, terms)
            health.append({"url": url, "status": result["status"]})
            if len(urls) == 1:
                urls.extend(result.get("attachments", [])[:2])
            for passage in result.get("excerpts", []):
                evidence.append({"id": "ev_" + digest([result["url"], passage]),
                                 "url": result["url"], "text": passage,
                                 "content_type": "original_page_excerpt",
                                 "source": event["source"], "source_kind": event["source_kind"],
                                 "published_at": event["published_at"], "retrieved_at": now_iso()})
        except (requests.RequestException, ValueError, OSError):
            health.append({"url": url, "status": "fetch_failed"})
    event["evidence"] = evidence[:6]
    event["evidence_health"] = health
    return event
