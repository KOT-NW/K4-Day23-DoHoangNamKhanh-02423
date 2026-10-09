"""check_citations.py - STUDENT IMPLEMENTS `check`.   Runs INSIDE the sandbox (standard library only).

research.py uploads this file to the sandbox and the lead agent runs it with the `execute` tool:
    python3 /tmp/work/research/check_citations.py [report.md] [sources.json]
It must exit 0 and print "OK: ..." when the report is consistent, else print each problem and exit 1.
"""
import json
import re
import sys

REPORT = "/tmp/work/report/report.md"
SOURCES = "/tmp/work/research/sources.json"

_REF_HEADING = re.compile(r"(?m)^##[ \t]+References[ \t]*$")
_CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
_GROUP = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\](?!\()")   # [3]  [1, 2]  [1-3]; not [3](link)
_URL = re.compile(r"https?://\S+")
_REF_LINE = re.compile(r"^\[(\d+)\]")


def _group_numbers(group):
    """Expand "[1, 2]" / "[1-3]" into the flat list of citation numbers it means."""
    numbers = []
    for part in re.split(r"\s*,\s*", group):
        span = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if span:
            a, b = int(span.group(1)), int(span.group(2))
            numbers.extend(range(a, b + 1) if 0 <= b - a <= 200 else [a, b])
        else:
            numbers.append(int(part))
    return numbers


def check(report_text, sources):
    """Return a list of problem strings (empty list = OK)."""
    if not isinstance(sources, list):
        return ["sources.json must be a JSON list of objects"]
    if not sources:
        return ["no sources in sources.json"]

    problems = []
    by_n = {}
    seen_urls = {}
    for source in sources:
        if not isinstance(source, dict):
            problems.append(f"source entry is not an object: {source!r}")
            continue
        n = source.get("n")
        if not isinstance(n, int) or isinstance(n, bool):
            problems.append(f"source has a non-integer n: {n!r}")
            continue
        url = source.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            problems.append(f"source [{n}] has an invalid url: {url!r}")
            continue
        if url in seen_urls:
            problems.append(f"duplicate url in sources.json: {url}")
            continue
        seen_urls[url] = n
        by_n[n] = url

    headings = list(_REF_HEADING.finditer(report_text))
    if not headings:
        problems.append("report has no '## References' section")
        body, ref_section = report_text, ""
    else:
        body = report_text[:headings[-1].start()]
        ref_section = report_text[headings[-1].end():]

    cited = set()
    for index, segment in enumerate(_CODE.split(body)):   # odd indexes are code spans: not citations
        if index % 2:
            continue
        for match in _GROUP.finditer(segment):
            cited.update(_group_numbers(match.group(1)))

    for n in sorted(cited):
        if n not in by_n:
            problems.append(f"[{n}] cited but missing from sources.json")
    for n in sorted(by_n):
        if n not in cited:
            problems.append(f"source [{n}] never cited")

    ref_lines = {}
    for line in ref_section.splitlines():
        match = _REF_LINE.match(line.strip())
        if not match:
            continue
        n = int(match.group(1))
        if n in ref_lines:
            problems.append(f"reference [{n}] appears more than once")
            continue
        ref_lines[n] = line
        if n not in by_n:
            problems.append(f"reference [{n}] has no matching source")
            continue
        urls = _URL.findall(line)
        if len(urls) != 1:
            problems.append(f"reference [{n}] must contain exactly one URL (found {len(urls)})")
        elif urls[0] != by_n[n]:
            problems.append(f"reference [{n}] URL does not match sources.json")

    for n in sorted(by_n):
        if n not in ref_lines:
            problems.append(f"reference [{n}] is missing")

    return problems


def main(argv):
    report_path = argv[1] if len(argv) > 1 else REPORT
    sources_path = argv[2] if len(argv) > 2 else SOURCES
    try:
        with open(report_path, encoding="utf-8") as f:
            report = f.read()
        with open(sources_path, encoding="utf-8") as f:
            sources = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"cannot read inputs: {exc}")
        return 1
    problems = check(report, sources)
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(sources)} sources, all citations resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
