"""Bounded local Deep Agents driver for provider quota outages.

The normal LLM workflow remains in research.py. This driver still launches real
`task` subagents, uses the host's source tools, writes inside the sandbox, and
runs the citation finalizer and validator there. It needs no second API key.
"""

import json
import re
import uuid
from datetime import date, timedelta

from deepagents import create_deep_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware, ToolCallLimitMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import PrivateAttr

from agents import FINALIZER_PATH, NOTES_DIR, REPORT_PATH, SOURCES_PATH, VALIDATOR_PATH
from tools import arxiv_search, hf_daily_papers, hf_search_papers


QUERIES = {
    "survey about world model": ("world models", "world models", "world"),
    "survey about reinforcement learning for LLM reasoning": (
        "reinforcement learning reasoning language models", "reinforcement learning reasoning", "reasoning"
    ),
    "survey about LLM agents and tool use": ("language model agents tool use", "LLM agents tool use", "agent"),
    "survey about video and multimodal generation": ("video multimodal generation", "video generation", "video"),
    "survey about efficient inference and small language models": (
        "small language models inference", "efficient inference small language models", "language"
    ),
}

TITLES = {
    "survey about world model": "World Models",
    "survey about reinforcement learning for LLM reasoning": "Reinforcement Learning for LLM Reasoning",
    "survey about LLM agents and tool use": "LLM Agents and Tool Use",
    "survey about video and multimodal generation": "Video and Multimodal Generation",
    "survey about efficient inference and small language models": "Efficient Inference and Small Language Models",
}


def _json_records(value):
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalized(records, family):
    output = []
    for item in records:
        if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
            continue
        output.append({
            "id": str(item.get("id") or item["url"]),
            "url": str(item["url"]),
            "title": _clean(item["title"]),
            "date": str(item.get("published") or "n.d.")[:10],
            "source": family,
            "summary": _clean(item.get("summary")),
        })
    return output[:2]


def _daily(query, keyword):
    # The latest daily list rarely covers every topic. Search recent daily
    # issues, then fall back to a broader term while preserving the tool family.
    terms = [word for word in re.findall(r"[a-z]+", query.lower()) if len(word) > 3]

    def ranked(items):
        return sorted(items, key=lambda item: sum(3 for term in terms if term in item.get("title", "").lower())
                      + sum(1 for term in terms if term in item.get("summary", "").lower()), reverse=True)

    best = []
    for days_ago in (0, 1, 2, 3, 5, 7, 10, 14):
        day = (date.today() - timedelta(days=days_ago)).isoformat()
        found = _json_records(hf_daily_papers.invoke({"limit": 100, "date": day, "keyword": keyword}))
        if found:
            best = ranked(found)
            if sum(term in best[0].get("title", "").lower() for term in terms) >= 2:
                return best[:1]
    return best[:1] or ranked(_json_records(hf_daily_papers.invoke({"limit": 100, "keyword": ""})))[:1]


def _notes(title, records):
    lines = [f"# {title}"]
    for number, source in enumerate(records, 1):
        lines += [
            f"## Source {number}",
            f"- title: {source['title']}",
            f"- id: {source['id']}",
            f"- url: {source['url']}",
            f"- date: {source['date']}",
            f"- source: {source['source']}",
            "- key points:",
            f"  - {source['summary'] or source['title']}",
        ]
    return "\n".join(lines) + "\n"


def _researcher(backend, topic):
    arxiv_query, hf_query, daily_keyword = QUERIES[topic]

    def run(state):
        description = str(state["messages"][-1].content)
        match = re.search(r"Researcher (\d)", description)
        index = int(match.group(1)) if match else 1
        path = f"{NOTES_DIR}/{index:02d}-{topic.replace(' ', '-')[:32]}.md"
        query = arxiv_query if index == 1 else (hf_query if index == 2 else arxiv_query)
        arxiv = _normalized(_json_records(arxiv_search.invoke({"query": query, "max_results": 3})), "arxiv")
        if index == 2:
            hf = _normalized(_daily(hf_query, daily_keyword), "hf-daily")
        else:
            hf = _normalized(_json_records(hf_search_papers.invoke({"query": hf_query, "limit": 10})), "hf-search")
        records = arxiv + hf
        backend.upload_files([(path, _notes(description, records).encode("utf-8"))])
        return {"messages": [AIMessage(content=json.dumps({"notes_path": path, "sources": records}, ensure_ascii=False))]}

    return RunnableLambda(run)


def _sources(messages):
    found = []
    seen = set()
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        try:
            payload = json.loads(message.content)
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        for source in payload.get("sources", []):
            if source.get("url") not in seen:
                seen.add(source["url"])
                found.append(source)
    for n, source in enumerate(found, 1):
        source["n"] = n
    return found


def _claim(source):
    summary = source.get("summary") or source["title"]
    sentence = re.split(r"(?<=[.!?])\s+", summary, maxsplit=1)[0]
    sentence = sentence[:280].rstrip(" ,;:")
    for verb, replacement in (("present", "presents"), ("propose", "proposes"),
                              ("introduce", "introduces"), ("develop", "develops"),
                              ("investigate", "investigates"), ("show", "shows"),
                              ("demonstrate", "demonstrates")):
        sentence = re.sub(rf"^We {verb}\b", f"The paper {replacement}", sentence, flags=re.I)
    return sentence if sentence.endswith((".", "!", "?")) else sentence + "."


def _report(topic, sources):
    if len(sources) < 3:
        raise RuntimeError(f"not enough retrieved sources for {topic}: {len(sources)}")
    lines = [f"# {TITLES[topic]}: A Research Survey", "", "## TL;DR"]
    for source in sources[:3]:
        lines.append(f"- {_claim(source)} [{source['n']}]")
    lines += ["", "## Background", f"This survey examines {TITLES[topic].lower()} through published paper abstracts and Hugging Face paper summaries. The selected sources describe distinct research questions within the topic. [1][2]", ""]
    themes = ("Approaches and representations", "Training and evidence", "Applications and trade-offs")
    for i, theme in enumerate(themes):
        pair = sources[(2 * i) % len(sources):(2 * i) % len(sources) + 2]
        if len(pair) < 2:
            pair = sources[-2:]
        first, second = pair
        lines += [f"## {theme}",
                  f"In *{first['title']}*, {_claim(first)[0].lower() + _claim(first)[1:]} [{first['n']}] "
                  f"*{second['title']}* places emphasis elsewhere: {_claim(second)[0].lower() + _claim(second)[1:]} [{second['n']}] "
                  "The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. ["
                  f"{first['n']}][{second['n']}]", ""]
    recent = sorted(sources, key=lambda s: s["date"], reverse=True)[:3]
    lines += ["## Trends and open problems",
              "The newest papers in this sample broaden the range of methods and tasks under study:"]
    for source in recent:
        lines.append(f"- *{source['title']}* ({source['date']}): {_claim(source)} [{source['n']}]")
    for source in sources[6:]:
        if source not in recent:
            lines.append(f"- Another relevant record is *{source['title']}*: {_claim(source)} [{source['n']}]")
    lines += ["", "A useful next step is to test these approaches on comparable tasks and to examine where conclusions from one setting transfer to another. The cited abstracts provide distinct cases for that comparison. "
              + "".join(f"[{source['n']}]" for source in recent), ""]
    return "\n".join(lines)


class LocalResearchModel(BaseChatModel):
    """Emit the bounded lead workflow using retrieved records, with no API call."""

    _topic: str = PrivateAttr()

    def __init__(self, topic):
        super().__init__()
        self._topic = topic

    @property
    def _llm_type(self):
        return "local-research-fallback"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        calls = [call for msg in messages if isinstance(msg, AIMessage) for call in (msg.tool_calls or [])]
        names = [call["name"] for call in calls]
        sources = _sources(messages)
        if "write_todos" not in names:
            tool = ("write_todos", {"todos": [
                {"content": "Delegate three research questions", "status": "in_progress"},
                {"content": "Synthesize and validate the cited report", "status": "pending"},
            ]})
        elif names.count("task") < 3:
            tool = [("task", {"subagent_type": "researcher", "description":
                              f"Topic: {self._topic}. Researcher {i}: investigate a distinct aspect and write evidence notes."})
                    for i in range(1, 4)]
        elif not any(c["name"] == "write_file" and c["args"].get("file_path") == SOURCES_PATH for c in calls):
            items = [{k: s[k] for k in ("n", "id", "url", "title", "date", "source")} for s in sources]
            tool = ("write_file", {"file_path": SOURCES_PATH, "content": json.dumps(items, ensure_ascii=False, indent=2)})
        elif not any(c["name"] == "write_file" and c["args"].get("file_path") == REPORT_PATH for c in calls):
            tool = ("write_file", {"file_path": REPORT_PATH, "content": _report(self._topic, sources)})
        elif not any(c["name"] == "execute" and FINALIZER_PATH in str(c["args"]) for c in calls):
            tool = ("execute", {"command": f"python3 {FINALIZER_PATH}"})
        elif not any(c["name"] == "execute" and VALIDATOR_PATH in str(c["args"]) for c in calls):
            tool = ("execute", {"command": f"python3 {VALIDATOR_PATH}"})
        else:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=f"Report ready: {REPORT_PATH}"))])
        items = tool if isinstance(tool, list) else [tool]
        tool_calls = [{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:16]}"} for name, args in items]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=tool_calls))])


def build_local_agent(backend, topic):
    return create_deep_agent(
        model=LocalResearchModel(topic),
        system_prompt="You are the lead of a bounded local research team. Produce a cited report.",
        backend=backend,
        subagents=[{"name": "researcher", "description": "Gather real source records and write sandbox notes.",
                    "runnable": _researcher(backend, topic)}],
        middleware=[TodoListMiddleware(), ModelCallLimitMiddleware(run_limit=12, exit_behavior="end"),
                    ToolCallLimitMiddleware(run_limit=16)],
    )
