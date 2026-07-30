"""Tool references inside prompts: `#search_docs` expands to a versioned lever.

Lives here rather than in behavior_core because the registry needs
search.TOOL_NAME, and agent already depends on behavior_core -- putting it there
would close the loop into a circular import.
"""

import re

from behavior_core.config import BehaviorConfig

from agent import search

MENTION = re.compile(r"#(\w+)")

TOOL_REGISTRY: dict[str, str] = {
    # tool name -> which lever holds its description text
    search.TOOL_NAME: "tool_description",
}


def expand_tools(prompt: str, config: BehaviorConfig) -> str:
    """Replace `#tool_name` with that tool's current description.

    Regex substitution rather than str.format() because prompts are free text in
    the console: a literal `{` typed into the editor used to raise KeyError from
    inside plan.run(), several layers away from anything the author touched.

    Unknown names pass through unchanged. That is what makes any accidental match
    harmless -- a markdown heading (`# Rules`) does not match at all because of
    the space, and `#1` matches but is not registered, so it stays literal.
    """

    def replace(match: re.Match) -> str:
        lever = TOOL_REGISTRY.get(match.group(1))
        return getattr(config, lever) if lever else match.group(0)

    return MENTION.sub(replace, prompt)


def catalog(config: BehaviorConfig) -> list[dict[str, str]]:
    """What the console's `#` autocomplete menu shows."""
    return [
        {"name": name, "lever": lever, "expands_to": getattr(config, lever)}
        for name, lever in TOOL_REGISTRY.items()
    ]
