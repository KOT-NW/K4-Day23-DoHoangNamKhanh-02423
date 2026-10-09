"""research.py - STUDENT IMPLEMENTS.  The main script.   Guide: GUIDE.md, part 3.

Usage:  python research.py "survey about world model"
Result: reports/<slug>.md   reports/<slug>.sources.json   reports/<slug>.meta.json
"""
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

from agents import FINALIZER_PATH, REPORT_PATH, SOURCES_PATH, VALIDATOR_PATH, WORKDIR, build_lead_agent
from model import make_model
from sandbox import download, open_sandbox, upload

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
VALIDATOR_SOURCE = ROOT / "check_citations.py"
FINALIZER_SOURCE = ROOT / "finalize_citations.py"   # provided: uploaded next to your validator


class _ProgressCallback(BaseCallbackHandler):
    """Print only event names so long agent runs show useful progress without dumping prompts or results."""

    def on_chat_model_start(self, serialized, messages, **kwargs):
        print("[progress] model call started", flush=True)

    def on_llm_end(self, response, **kwargs):
        print("[progress] model call finished", flush=True)

    def on_llm_error(self, error, **kwargs):
        print(f"[progress] model call failed: {type(error).__name__}", flush=True)

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "tool") if isinstance(serialized, dict) else "tool"
        print(f"[progress] {name} started", flush=True)

    def on_tool_end(self, output, **kwargs):
        print("[progress] tool finished", flush=True)

    def on_tool_error(self, error, **kwargs):
        print(f"[progress] tool failed: {type(error).__name__}", flush=True)


def slugify(topic):
    """Turn a topic into a safe file name: lower case, runs of non-word characters become one "-", max 60 chars,
    never empty (fall back to "topic"). The topic is user input: "../../x" must not escape reports/."""
    slug = re.sub(r"[^\w]+", "-", (topic or "").strip().lower()).strip("-")
    return slug[:60].strip("-") or "topic"


def build_prompt(topic):
    """The user message sent to the lead agent."""
    return (
        f"Research topic: {topic}\n\n"
        "Run the full deep-research workflow described in your system prompt and produce the cited survey report."
    )


def prepare_model(model):
    """Disable DeepSeek's default thinking mode.

    DeepSeek returns a `reasoning_content` field in thinking mode and rejects (HTTP 400) any follow-up request that
    carries `tools` but not that field; ChatOpenAI/ChatDeepSeek drop it, so tool calling would break. Disabling
    thinking keeps tool calling working and is a no-op for every other provider.
    """
    model_name = str(getattr(model, "model_name", None) or getattr(model, "model", "") or "").lower()
    base_url = str(getattr(model, "openai_api_base", None) or "").lower()
    provider = type(model).__module__.lower()
    # OpenRouter checks the requested maximum against the key's credit limit
    # before generating anything. The provider default can be tens of
    # thousands of tokens even though a single agent step needs far less.
    if hasattr(model, "max_tokens"):
        model.max_tokens = 2048
    if "deepseek" in model_name or "deepseek" in base_url or "deepseek" in provider:
        extra = dict(getattr(model, "extra_body", None) or {})
        extra.setdefault("thinking", {"type": "disabled"})
        model.extra_body = extra

    # Keep a slow or unavailable OpenAI-compatible endpoint from retrying each request
    # for several minutes. The configured model is already a Flash model; bound request
    # time and SDK retries so the workflow can fail over to its other research sources.
    if hasattr(model, "root_client") and hasattr(model, "request_timeout"):
        request_timeout = 45.0
        model.request_timeout = request_timeout
        root_client = model.root_client.with_options(timeout=request_timeout, max_retries=0)
        model.root_client = root_client
        model.client = root_client.chat.completions
        root_async_client = model.root_async_client.with_options(timeout=request_timeout, max_retries=0)
        model.root_async_client = root_async_client
        model.async_client = root_async_client.chat.completions
    return model


def summarize(messages, elapsed, model_name):
    """Return {"model", "elapsed_s", "subagent_calls", "tool_calls": {name: count}, "tokens": {"input", "output"}}.

    PSEUDO-CODE: walk the lead's messages; for every message with tool_calls count call["name"] (subagent_calls = the
    count of "task"); add the input/output token counts from each message's usage_metadata when present.
    (Lead messages only: subagent tokens are not included, so this undercounts the real cost.)
    elapsed_s rounded to 0.1.
    """
    tool_calls = Counter()
    subagent_calls = 0
    tokens_in = 0
    tokens_out = 0
    for message in messages or []:
        for call in getattr(message, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            if not name:
                continue
            tool_calls[name] += 1
            if name == "task":
                subagent_calls += 1
        usage = getattr(message, "usage_metadata", None)
        if isinstance(usage, dict):
            tokens_in += usage.get("input_tokens") or 0
            tokens_out += usage.get("output_tokens") or 0
    return {
        "model": model_name,
        "elapsed_s": round(elapsed, 1),
        "subagent_calls": subagent_calls,
        "tool_calls": dict(tool_calls),
        "tokens": {"input": tokens_in, "output": tokens_out},
    }


def save_outputs(backend, topic, messages, elapsed, model_name, reports_dir=REPORTS):
    """Download the report from the sandbox and write the three files into reports_dir. Return the report path.

    PSEUDO-CODE:
      files = download(backend, [REPORT_PATH, SOURCES_PATH])
      if the report is missing/empty or sources.json is missing/invalid JSON: raise RuntimeError and WRITE NOTHING
          (a failed run must never leave an empty or half-written report behind)
      write <slug>.sources.json, <slug>.meta.json (topic + summarize(...) + n_sources + source_families: the sorted
      distinct "source" values of sources.json) and <slug>.md
    """
    files = download(backend, [REPORT_PATH, SOURCES_PATH])
    report_bytes = files.get(REPORT_PATH)
    sources_bytes = files.get(SOURCES_PATH)

    if not report_bytes or not report_bytes.strip():
        raise RuntimeError("the agent did not produce a report (report.md is missing or empty)")
    if not sources_bytes:
        raise RuntimeError("the agent did not produce sources.json")

    try:
        sources = json.loads(sources_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"sources.json is not valid JSON: {exc}") from exc
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("sources.json must be a non-empty JSON array")

    families = sorted({str(s.get("source")) for s in sources if isinstance(s, dict) and s.get("source")})
    meta = {"topic": topic, **summarize(messages, elapsed, model_name),
            "n_sources": len(sources), "source_families": families}

    slug = slugify(topic)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{slug}.sources.json").write_bytes(sources_bytes)
    (reports_dir / f"{slug}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = reports_dir / f"{slug}.md"
    report_path.write_bytes(report_bytes)
    return report_path


def main(topic):
    """Return the process exit code (0 ok, 1 failed run, 2 no topic).

    PSEUDO-CODE:
      empty topic -> print usage to stderr, return 2
      model = make_model(); start = time.monotonic()
      with open_sandbox() as backend:                # the sandbox is always cleaned up, even on errors
          backend.execute("mkdir -p <WORKDIR>/research/notes <WORKDIR>/report")
          upload(backend, {VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(), FINALIZER_PATH: FINALIZER_SOURCE.read_bytes()})
          agent = build_lead_agent(backend, model)
          result = agent.invoke({"messages": [{"role": "user", "content": build_prompt(topic)}]},
                                config={"recursion_limit": 300})
          save_outputs(...); on RuntimeError print "FAILED: ..." to stderr and return 1
      print where the report was saved; return 0
    """
    if not topic or not topic.strip():
        print('usage: python research.py "<topic>"', file=sys.stderr)
        return 2

    local_fallback = os.getenv("LAB_LOCAL_FALLBACK") == "1"
    if local_fallback:
        from local_fallback import build_local_agent

        model_name = "local-source-backed-fallback"
    else:
        model = prepare_model(make_model())
        model_name = (getattr(model, "model_name", None) or getattr(model, "model", None)
                      or getattr(model, "model_id", None) or type(model).__name__)

    start = time.monotonic()
    with open_sandbox() as backend:
        backend.execute(f"mkdir -p {WORKDIR}/research/notes {WORKDIR}/report")
        upload(backend, {
            VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(),
            FINALIZER_PATH: FINALIZER_SOURCE.read_bytes(),
        })
        agent = build_local_agent(backend, topic) if local_fallback else build_lead_agent(backend, model)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": build_prompt(topic)}]},
            config={"recursion_limit": 300, "callbacks": [_ProgressCallback()]},
        )
        elapsed = time.monotonic() - start
        messages = result.get("messages", []) if isinstance(result, dict) else []
        trace = summarize(messages, elapsed, str(model_name))
        print(f"[progress] messages={len(messages)} tool_calls={trace['tool_calls']}", flush=True)
        try:
            report_path = save_outputs(backend, topic, messages, elapsed, model_name)
        except RuntimeError as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            return 1

    print(f"report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:])))
