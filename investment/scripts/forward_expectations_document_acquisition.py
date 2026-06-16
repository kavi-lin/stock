"""Bounded document acquisition for Forward Expectations.

This module turns discovered SEC filing URLs into normalized text bundles. It is
not an evidence extractor: downloaded text still has to pass
forward_expectations_primary_sources.py promotion gates before it can influence an
adapter. Company website/IR roots are intentionally not fetched here.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "investment", "invest_logs", "forward_expectations_documents")
CACHE_TTL_HOURS = 24 * 30
MAX_BYTES = 2_500_000
TIMEOUT = 20
DEFAULT_UA = "AI Investment Committee research@example.com"

ALLOWED_HOSTS = {"www.sec.gov", "sec.gov", "data.sec.gov"}
ALLOWED_SOURCE_TYPES = {"company_filing"}
ALLOWED_STATUS = {"metadata_only", "content_available"}


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def _cache_path(url: str) -> str:
    return os.path.join(CACHE_DIR, f"{_cache_key(url)}.json")


def _cache_get(url: str) -> dict | None:
    path = _cache_path(url)
    try:
        if (time.time() - os.path.getmtime(path)) / 3600 > CACHE_TTL_HOURS:
            return None
    except OSError:
        return None
    data = _read_json(path)
    return data if isinstance(data, dict) else None


def _cache_put(url: str, payload: dict) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(url), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def url_policy(candidate: dict) -> tuple[bool, str]:
    url = candidate.get("source_url") or candidate.get("source_ref")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False, "missing_http_url"
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in ALLOWED_HOSTS:
        return False, "host_not_allowlisted"
    if candidate.get("source_type") not in ALLOWED_SOURCE_TYPES:
        return False, "source_type_not_fetchable"
    if candidate.get("status") not in ALLOWED_STATUS:
        return False, "source_status_not_fetchable"
    path = parsed.path.lower()
    if host == "data.sec.gov":
        if not path.endswith(".json"):
            return False, "data_sec_only_json_manifest"
        return False, "sec_manifest_metadata_only"
    if "/archives/edgar/data/" not in path:
        return False, "sec_archives_only"
    if not path.endswith((".htm", ".html", ".txt")):
        return False, "unsupported_sec_document_extension"
    return True, "allowlisted_sec_filing_document"


def normalize_document_text(raw: str, content_type: str | None = None) -> str:
    text = raw or ""
    looks_html = "<html" in text[:1000].lower() or "<body" in text[:2000].lower() or "<p" in text[:2000].lower()
    if looks_html or (content_type or "").lower().startswith("text/html"):
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
    else:
        text = html.unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fetch_url(url: str) -> tuple[str | None, dict]:
    headers = {
        "User-Agent": os.getenv("EDGAR_UA") or DEFAULT_UA,
        "Accept-Encoding": "gzip, deflate",
    }
    response = requests.get(url, headers=headers, timeout=TIMEOUT)
    meta = {
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "content_length": response.headers.get("content-length"),
    }
    if response.status_code != 200:
        return None, meta
    content = response.content[:MAX_BYTES + 1]
    if len(content) > MAX_BYTES:
        meta["truncated"] = True
        content = content[:MAX_BYTES]
    else:
        meta["truncated"] = False
    encoding = response.encoding or "utf-8"
    try:
        return content.decode(encoding, errors="replace"), meta
    except LookupError:
        return content.decode("utf-8", errors="replace"), meta


def acquire_documents(source_discovery: dict, *, no_fetch: bool = True,
                      max_documents: int = 3) -> dict:
    documents = []
    skipped = []
    cache_hits = 0
    network_fetches = 0
    for candidate in (source_discovery or {}).get("candidates") or []:
        allowed, reason = url_policy(candidate)
        if not allowed:
            skipped.append({
                "source_id": candidate.get("source_id"),
                "source_url": candidate.get("source_url"),
                "reason": reason,
            })
            continue
        url = candidate.get("source_url") or candidate.get("source_ref")
        cached = _cache_get(url)
        if cached:
            documents.append(cached)
            cache_hits += 1
            continue
        if no_fetch or len(documents) >= max_documents:
            skipped.append({
                "source_id": candidate.get("source_id"),
                "source_url": url,
                "reason": "fetch_disabled" if no_fetch else "max_documents_reached",
            })
            continue
        raw, fetch_meta = _fetch_url(url)
        network_fetches += 1
        if raw is None:
            skipped.append({
                "source_id": candidate.get("source_id"),
                "source_url": url,
                "reason": "fetch_failed",
                "fetch_meta": fetch_meta,
            })
            continue
        text = normalize_document_text(raw, fetch_meta.get("content_type"))
        if not text:
            skipped.append({
                "source_id": candidate.get("source_id"),
                "source_url": url,
                "reason": "empty_normalized_text",
                "fetch_meta": fetch_meta,
            })
            continue
        document = {
            "document_id": f"document:{candidate.get('source_id')}",
            "source_type": candidate.get("source_type"),
            "source_ref": url,
            "source_url": url,
            "published_at": candidate.get("published_at"),
            "period": candidate.get("period"),
            "form": candidate.get("form"),
            "filing_family": candidate.get("filing_family"),
            "content": text,
            "content_length": len(text),
            "status": "normalized_text",
            "numeric_eligible": False,
            "fetch_meta": fetch_meta,
            "policy": "Document text must pass primary-source extraction before promotion.",
        }
        _cache_put(url, document)
        documents.append(document)
    return {
        "ticker": (source_discovery or {}).get("ticker"),
        "cache_first": True,
        "network_fetch_used": network_fetches > 0,
        "summary": {
            "document_count": len(documents),
            "skipped_count": len(skipped),
            "cache_hit_count": cache_hits,
            "network_fetch_count": network_fetches,
        },
        "documents": documents,
        "skipped": skipped,
        "policy": (
            "Only allowlisted SEC filing document URLs are fetched. "
            "Normalized text is not evidence until promotion gates pass."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Bounded document acquisition for Forward Expectations")
    ap.add_argument("--source-discovery-file", required=True)
    ap.add_argument("--fetch", action="store_true", help="allow network fetch for allowlisted SEC documents")
    ap.add_argument("--max-documents", type=int, default=3)
    args = ap.parse_args()
    source_discovery = _read_json(args.source_discovery_file)
    if not isinstance(source_discovery, dict):
        print(json.dumps({"error": "source discovery file must be a JSON object"}))
        sys.exit(1)
    result = acquire_documents(
        source_discovery,
        no_fetch=not args.fetch,
        max_documents=args.max_documents,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
