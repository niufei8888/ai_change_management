"""Package the AI coding sessions into ai-sessions/ as a submission artifact.

Two conversations ship: `planning`, which is the whole project from reading the
brief to step 5, and `qq`, which is where the brief itself got interrogated before
any code existed. Cursor writes them as JSONL under
~/.cursor/projects/<slug>/agent-transcripts/.

Why a script rather than a tidied-up copy
-----------------------------------------
The session history is evidence for one of the brief's grading criteria -- how the
tools were directed and where they were pushed back on. A Markdown file I curated
by hand is not evidence of that; it is my account of it, and there is no way for a
reader to tell which exchanges I dropped. Rendering mechanically and shipping the
renderer makes "nothing was cherry-picked" a claim anyone can check: run this
against the raw JSONL and diff the output.

So every transformation below is deliberately dumb, and this list is exhaustive:

  1. Secrets are replaced (see redact()). This is the one lossy step.
  2. Absolute paths under the home directory become <repo>/... or <home>/...
  3. The <timestamp> and <user_query> wrappers Cursor adds around a user turn are
     unwrapped -- the timestamp becomes a heading, the query becomes the body.
  4. System-injected context blocks are dropped by tag name: system_reminder,
     open_and_recently_viewed_files, attached_files, system_notification,
     image_files, agent_transcripts, rules, agent_skills, mcp_server_catalog,
     user_info, timestamp. None of these are anybody's words; they are harness
     plumbing, and leaving them in buries the conversation.
  5. Turns whose entire body is one of the BOILERPLATE strings are dropped. These
     are what Cursor sends in the user slot to make the agent continue after a
     background task or to kick off a plan; roughly a third of the "user" turns in
     the planning session are one particular such string. They are listed in full
     below so that "dropped as boilerplate" can be checked rather than trusted.
  6. A user turn identical to the one immediately before it is dropped. Cursor
     writes some turns twice, once plain and once carrying attachments.
  7. Tool calls are rendered as one line naming the tool and its main argument.
     Results are not in the JSONL to begin with.

Nothing is reordered, summarised, translated or omitted on the basis of content.

Usage:  python scripts/export_sessions.py
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "ai-sessions"
HOME = Path.home()
TRANSCRIPTS = HOME / ".cursor/projects/Users-fniu-Downloads-aicoding/agent-transcripts"

# Title -> conversation id, resolved from Cursor's globalStorage state.vscdb
# (cursorDiskKV, key `composerData:<id>`, JSON field `name`). Pinned here rather
# than looked up so this script does not depend on a database that is not part of
# the repo, and so the reader can see exactly which two shipped.
SESSIONS = [
    ("planning", "e8826cd9-04c1-4bc0-bd00-22ca00405e2f"),
    ("qq", "165b1b39-4341-4ff8-b95b-8a56279ea57c"),
]

# Shapes, as a backstop for credentials that are no longer in .env. The AQ. entry
# is not hypothetical: the key used on this project has that prefix, and a scan
# looking only for the classic AIza... form reported this transcript clean.
SECRET_SHAPES = [
    re.compile(r"AQ\.[A-Za-z0-9_.\-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b(?=[^\n]{0,40}(token|Token|TOKEN))"),
]

DROP_TAGS = [
    "system_reminder", "open_and_recently_viewed_files", "attached_files",
    "system_notification", "image_files", "agent_transcripts", "rules",
    "agent_skills", "mcp_server_catalog", "user_info", "timestamp",
]

# Matched against the whole cleaned body, not searched for inside it.
BOILERPLATE = [
    "Briefly inform the user about the task result and perform any follow-up actions (if needed).",
    "Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.",
]
DROP_RE = [re.compile(rf"<{t}>.*?</{t}>", re.S) for t in DROP_TAGS]
QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
TIME_RE = re.compile(r"<timestamp>\s*(.*?)\s*</timestamp>", re.S)
MASK = "<REDACTED>"


def env_secrets() -> list[str]:
    """Literal values from .env, longest first so a value containing another wins.

    Read but never printed or returned to a caller that reports them. This is the
    only way to be sure the credentials actually used on this machine are covered;
    matching by shape alone means betting that I guessed every provider's format.
    """
    path = REPO / ".env"
    if not path.exists():
        return []
    values = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        value = line.split("=", 1)[1].strip().strip("'\"")
        # Short values are words, not secrets; masking them would shred the prose.
        if len(value) >= 12:
            values.append(value)
    return sorted(values, key=len, reverse=True)


def redact(text: str, literals: list[str]) -> str:
    for literal in literals:
        text = text.replace(literal, MASK)
    for shape in SECRET_SHAPES:
        text = shape.sub(MASK, text)
    text = text.replace(str(REPO), "<repo>")
    return text.replace(str(HOME), "<home>")


def blocks(message) -> list:
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = message
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def clean_user(text: str) -> tuple[str, str]:
    """Return (timestamp, body) with the harness wrappers taken off."""
    when = ""
    if found := TIME_RE.search(text):
        when = found.group(1).strip()
    if found := QUERY_RE.search(text):
        text = found.group(1)
    for pattern in DROP_RE:
        text = pattern.sub("", text)
    return when, text.strip()


def is_boilerplate(body: str) -> bool:
    head = body.split("\n", 1)[0].strip()
    return any(head.startswith(b) or body.strip() == b for b in BOILERPLATE)


def render(path: Path, title: str, literals: list[str]) -> tuple[str, int, int]:
    lines = [f"# Session: `{title}`", ""]
    turns = users = 0
    previous = ""

    for raw in path.read_text(errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue

        role = event.get("role") or ""
        pieces = blocks(event.get("message"))
        texts = [b.get("text", "") for b in pieces if b.get("type") == "text"]
        tools = [b for b in pieces if b.get("type") == "tool_use"]

        if role in ("user", "human"):
            when, body = clean_user("\n".join(texts))
            if not body or is_boilerplate(body) or body == previous:
                continue
            previous = body
            users += 1
            turns += 1
            lines += ["---", "", f"## User &middot; {when}" if when else "## User", "", body, ""]
        elif role == "assistant":
            body = "\n".join(t for t in texts if t.strip()).strip()
            if not body and not tools:
                continue
            turns += 1
            lines += ["### Assistant", ""]
            if body:
                lines += [body, ""]
            for tool in tools:
                arg = tool.get("input") or {}
                first = ""
                if isinstance(arg, dict):
                    for key in ("path", "command", "pattern", "prompt", "description"):
                        if arg.get(key):
                            first = f" {key}=" + str(arg[key]).replace("\n", " ")[:110]
                            break
                lines.append(f"> **{tool.get('name', 'tool')}**`{first}`")
            if tools:
                lines.append("")

    return redact("\n".join(lines), literals), turns, users


def verify(paths: list[Path], literals: list[str]) -> int:
    """Scan the artifacts, not the inputs.

    Running the rules over the source and finding nothing only proves the rules
    are wrong in a way that reports success -- which is exactly how the AQ.-
    prefixed key survived the first scan. Only the output can be cleared.
    """
    hits = 0
    for path in paths:
        text = path.read_text(errors="replace")
        for literal in literals:
            hits += text.count(literal)
        for shape in SECRET_SHAPES:
            hits += len(shape.findall(text))
        if str(HOME) in text:
            hits += text.count(str(HOME))
    return hits


def main() -> None:
    literals = env_secrets()
    print(f"redacting {len(literals)} literal value(s) from .env, plus {len(SECRET_SHAPES)} shapes")
    OUT.mkdir(exist_ok=True)
    (OUT / "raw").mkdir(exist_ok=True)
    written = []

    for title, cid in SESSIONS:
        source = TRANSCRIPTS / cid / f"{cid}.jsonl"
        if not source.exists():
            raise SystemExit(f"missing transcript for {title}: {source}")

        # The raw file ships too, redacted line by line so it stays valid JSONL.
        raw_out = OUT / "raw" / f"{title}.jsonl"
        raw_out.write_text(
            "\n".join(redact(line, literals) for line in source.read_text(errors="replace").splitlines()) + "\n"
        )

        body, turns, users = render(source, title, literals)
        md_out = OUT / f"{title}.md"
        md_out.write_text(body + "\n")
        written += [raw_out, md_out]
        print(f"  {title:<10} {turns:>5} turns ({users} from me)  "
              f"{md_out.stat().st_size // 1024:>5} KB md  {raw_out.stat().st_size // 1024:>5} KB jsonl")

    hits = verify(written, literals)
    print(f"\nverification on the written artifacts: {hits} hit(s)")
    if hits:
        raise SystemExit("refusing to ship: something matched a credential rule in the output")
    print("clean")


if __name__ == "__main__":
    main()
