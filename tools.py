"""tools.py - STUDENT IMPLEMENTS.  Source tools for the research agents.   Guide: GUIDE.md, part 1.

Rules for every tool:
  * runs on the HOST (not in the sandbox): API keys must never enter the sandbox;
  * returns a STRING (JSON text of compact records) and NEVER raises:
        "NO RESULTS"  when the source answers with nothing,
        "ERROR: ..."  when the source keeps failing after the retries (the agent then tries another source);
  * the docstring is the tool description the LLM reads: keep it precise (what it does, what it returns, when to use it).
Try your tools without any agent:   python tools.py
"""
import json
import os
import random
import re
import threading
import time
import xml.etree.ElementTree as ET

import httpx
from langchain_core.tools import tool

# ---- constants (given) ----
ARXIV_URL = "https://export.arxiv.org/api/query"  # https only: http answers 301
HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HF_SEARCH_URL = "https://huggingface.co/api/papers/search"
EXA_URL = "https://mcp.exa.ai/mcp"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
ARXIV_MIN_INTERVAL = 3.0          # arXiv etiquette: at least 3 seconds between calls
SUMMARY_CHARS = 600               # keep records compact so they do not flood the context
FETCH_CHARS = 12000               # web_fetch truncation


def _clamp(value, low, high):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = low
    return max(low, min(high, value))


def _norm(text):
    return " ".join((text or "").split())


class RetryableError(Exception):
    """Given. Raise it inside a call to ask with_retry to wait and try again (retry_after in seconds, optional)."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


# ---- TODO 1: retry helper ----
def with_retry(fn, *, attempts=5, base=1.0, cap=30.0):
    """Call fn(); when it raises RetryableError, wait and call it again.

    PSEUDO-CODE:
      for attempt in 0 .. attempts-1:
          try: return fn()
          except RetryableError as e:
              if this was the last attempt: raise
              delay = e.retry_after if the server told us, else exponential backoff base * 2**attempt
              cap the delay at `cap` seconds; add random jitter to the exponential case
              sleep(delay)
    Use it to wrap EVERY network call below. Also treat these as retryable: HTTP 429/500/502/503/504,
    httpx.TransportError (timeouts, connection resets). Read the Retry-After header when present.
    """
    attempts = max(1, int(attempts))
    for attempt in range(attempts):
        try:
            return fn()
        except RetryableError as exc:
            if attempt == attempts - 1:
                raise
            if exc.retry_after is not None:
                delay = min(max(0.0, float(exc.retry_after)), cap)
            else:
                delay = min(base * (2 ** attempt), cap) + random.uniform(0.0, base)
            time.sleep(delay)


def _retry_after_seconds(response):
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def _request(client, method, url, **kwargs):
    """One HTTP request that maps retryable failures to RetryableError and other bad statuses to exceptions."""
    try:
        response = client.request(method, url, **kwargs)
    except httpx.TransportError as exc:
        raise RetryableError(f"network error: {exc}") from exc
    if response.status_code in RETRYABLE_STATUS:
        raise RetryableError(f"HTTP {response.status_code}", retry_after=_retry_after_seconds(response))
    response.raise_for_status()
    return response


# ---- TODO 2: arXiv ----
_arxiv_lock = threading.Lock()
_last_arxiv_call = 0.0


def _arxiv_throttle():
    """Serialize arXiv calls and keep at least ARXIV_MIN_INTERVAL seconds between them."""
    global _last_arxiv_call
    with _arxiv_lock:
        gap = ARXIV_MIN_INTERVAL - (time.monotonic() - _last_arxiv_call)
        if gap > 0:
            time.sleep(gap)
        _last_arxiv_call = time.monotonic()


def _atom_text(entry, path):
    node = entry.find(path, ATOM_NS)
    return "" if node is None or node.text is None else node.text


@tool
def arxiv_search(query: str, max_results: int = 10) -> str:
    """Search arXiv papers by keywords, newest first. Returns a JSON list of {id, url, published, title, summary}."""
    try:
        words = re.findall(r"[A-Za-z0-9]+", query or "")
        terms = [w for w in words if w.upper() not in {"AND", "OR", "NOT"}]
        if not terms:
            return "NO RESULTS"
        params = {
            "search_query": " AND ".join(f"all:{term}" for term in terms),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": _clamp(max_results, 1, 30),
            "start": 0,
        }

        def fetch():
            _arxiv_throttle()
            with httpx.Client(timeout=30) as client:
                return _request(client, "GET", ARXIV_URL, params=params)

        response = with_retry(fetch, attempts=6, base=1.0, cap=60.0)
        root = ET.fromstring(response.text)
        records = []
        for entry in root.findall("atom:entry", ATOM_NS):
            raw_id = _atom_text(entry, "atom:id").strip()
            paper_id = re.sub(r"v\d+$", "", raw_id.rsplit("/", 1)[-1])
            if not paper_id:
                continue
            records.append({
                "id": paper_id,
                "url": f"https://arxiv.org/abs/{paper_id}",
                "published": _atom_text(entry, "atom:published")[:10],
                "title": _norm(_atom_text(entry, "atom:title")),
                "summary": _norm(_atom_text(entry, "atom:summary"))[:SUMMARY_CHARS],
            })
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


# ---- TODO 3: Hugging Face ----
def _hf_record(paper, item, prefer_ai_summary=False):
    pid = paper.get("id")
    if not pid:
        return None
    summary = paper.get("ai_summary") if prefer_ai_summary else None
    summary = summary or paper.get("summary") or item.get("summary") or ""
    published = paper.get("publishedAt") or item.get("publishedAt") or ""
    return {
        "id": pid,
        "url": f"https://huggingface.co/papers/{pid}",
        "published": str(published)[:10],
        "title": _norm(paper.get("title") or item.get("title") or ""),
        "summary": _norm(summary)[:SUMMARY_CHARS],
        "upvotes": int(paper.get("upvotes") or 0),
        "github": paper.get("githubRepo") or "",
        "stars": int(paper.get("githubStars") or 0),
    }


def _hf_items(response):
    data = response.json()
    return data if isinstance(data, list) else []


@tool
def hf_daily_papers(limit: int = 30, date: str = "", keyword: str = "") -> str:
    """Hugging Face Daily Papers = what is trending in AI research. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars} sorted by upvotes. `date` is YYYY-MM-DD (empty = latest).
    `keyword` filters title/summary; there is no topic search on this endpoint (use hf_search_papers for a topic)."""
    try:
        params = {"limit": _clamp(limit, 1, 100)}
        if date:
            params["date"] = date

        def fetch():
            with httpx.Client(timeout=30) as client:
                return _request(client, "GET", HF_DAILY_URL, params=params)

        response = with_retry(fetch)
        records = []
        for item in _hf_items(response):
            if not isinstance(item, dict):
                continue
            paper = item.get("paper") if isinstance(item.get("paper"), dict) else {}
            record = _hf_record(paper, item)
            if record:
                records.append(record)
        if keyword:
            needle = keyword.lower()
            records = [r for r in records if needle in f"{r['title']} {r['summary']}".lower()]
        records.sort(key=lambda r: r["upvotes"], reverse=True)
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


@tool
def hf_search_papers(query: str, limit: int = 10) -> str:
    """Search Hugging Face papers by topic. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars}."""
    try:
        params = {"q": query, "limit": _clamp(limit, 1, 50)}

        def fetch():
            with httpx.Client(timeout=30) as client:
                return _request(client, "GET", HF_SEARCH_URL, params=params)

        response = with_retry(fetch)
        records = []
        for item in _hf_items(response):
            if not isinstance(item, dict):
                continue
            paper = item.get("paper") if isinstance(item.get("paper"), dict) else {}
            record = _hf_record(paper, item, prefer_ai_summary=True)
            if record:
                records.append(record)
        records.sort(key=lambda r: r["upvotes"], reverse=True)
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


# ---- TODO 4: web search / fetch through the Exa MCP endpoint ----
def _exa_key():
    return (os.getenv("EXA_API_KEY") or "").strip()


def _redact(text):
    """Never let the Exa API key (which rides in the URL) leak into anything the agent sees."""
    key = _exa_key()
    return str(text).replace(key, "***") if key else str(text)


def _looks_rate_limited(text):
    lowered = (text or "").lower()
    return "rate limit" in lowered or "free mcp" in lowered or "exaapikey" in lowered


def _meta_rate_limited(result):
    """Exa flags throttling in a `_meta` block; check both the result and its content parts."""
    candidates = [result.get("_meta")]
    for part in result.get("content") or []:
        if isinstance(part, dict):
            candidates.append(part.get("_meta"))
    for meta in candidates:
        if isinstance(meta, dict):
            for key, value in meta.items():
                if "limit" in str(key).lower() and value:
                    return True
    return False


def _parse_sse(text):
    """Extract the JSON-RPC object from an SSE (or plain JSON) Exa reply."""
    events = []
    data_lines = []
    for line in text.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
        elif not line.strip() and data_lines:
            events.append("\n".join(data_lines))
            data_lines = []
    if data_lines:
        events.append("\n".join(data_lines))
    for event in events:
        try:
            obj = json.loads(event)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("result" in obj or "error" in obj):
            return obj
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"cannot parse Exa response: {exc}") from exc


def _result_text(result):
    parts = result.get("content") or []
    return "\n".join(
        part.get("text", "") for part in parts
        if isinstance(part, dict) and part.get("type") == "text"
    )


def _exa_call(tool_name, arguments):
    """Call one Exa MCP tool over plain HTTP JSON-RPC and return its `result` (or raise)."""
    key = _exa_key()
    endpoint = f"{EXA_URL}?exaApiKey={key}" if key else EXA_URL
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": tool_name, "arguments": arguments}}
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def call():
        with httpx.Client(timeout=35) as client:
            response = _request(client, "POST", endpoint, headers=headers, json=payload)
        data = _parse_sse(response.text)
        error = data.get("error")
        if error:
            message = error.get("message", error) if isinstance(error, dict) else error
            if _looks_rate_limited(str(message)):
                raise RetryableError(str(message))
            raise RuntimeError(f"Exa JSON-RPC error: {message}")
        result = data.get("result") or {}
        text = _result_text(result)
        if result.get("isError") or _meta_rate_limited(result):
            if _looks_rate_limited(text):
                raise RetryableError(text or "Exa rate limited")
            raise RuntimeError(text or "Exa tool error")
        if _looks_rate_limited(text):
            raise RetryableError(text)
        return result

    return with_retry(call, attempts=3, base=1.0, cap=15.0)


@tool
def web_search(query: str, objective: str = "", num_results: int = 5) -> str:
    """Search the web (Exa). Describe the ideal page in natural language. Returns clean text of the top results with URLs."""
    try:
        objective = (objective or "").strip() or f"Find authoritative, up-to-date pages that answer: {query}"
        result = _exa_call("web_search_exa", {
            "query": query,
            "objective": objective,
            "numResults": _clamp(num_results, 1, 10),
        })
        text = _result_text(result).strip()
        return text or "NO RESULTS"
    except Exception as exc:
        return f"ERROR: {_redact(f'{type(exc).__name__}: {exc}')}"


@tool
def web_fetch(url: str) -> str:
    """Read the full content of one web page (e.g. an arXiv abstract page) as markdown. Long pages are truncated."""
    try:
        result = _exa_call("web_fetch_exa", {"urls": [url]})
        text = _result_text(result).strip()
        return text[:FETCH_CHARS] if text else "NO RESULTS"
    except Exception as exc:
        return f"ERROR: {_redact(f'{type(exc).__name__}: {exc}')}"


# ---- TODO 5: registry (the researcher subagent gets exactly these) ----
SOURCE_TOOLS = [arxiv_search, hf_daily_papers, hf_search_papers, web_search, web_fetch]


if __name__ == "__main__":
    for name, fn, args in [
        ("arxiv_search", arxiv_search, {"query": "world model", "max_results": 3}),
        ("hf_daily_papers", hf_daily_papers, {"limit": 20}),
        ("hf_search_papers", hf_search_papers, {"query": "world model", "limit": 3}),
        ("web_search", web_search, {"query": "survey paper on world models", "num_results": 2}),
        ("web_fetch", web_fetch, {"url": "https://arxiv.org/abs/1803.10122"}),
    ]:
        try:
            print(f"== {name}\n{fn.invoke(args)[:400]}\n")
        except NotImplementedError as exc:
            print(f"== {name}: not implemented yet ({exc})\n")
