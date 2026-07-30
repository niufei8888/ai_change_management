from agent import llm, tools
from behavior_core.config import BehaviorConfig

INSUFFICIENT_NOTE = (
    "\n\nThe search did not turn up enough to answer this. Say so plainly and briefly. "
    "Do not attempt an answer from general knowledge."
)


def run(
    question: str, evidence: list[dict[str, str]], config: BehaviorConfig, sufficient: bool
) -> tuple[str, llm.LLMResult]:
    """Write the answer. Free text, so no schema here."""
    blocks = "\n\n".join(
        f"[{item['article_title']} > {item['heading']}]\n{item['text']}" for item in evidence
    ) or "(no evidence was retrieved)"

    system = tools.expand_tools(config.synthesize_prompt, config)
    if not sufficient:
        system += INSUFFICIENT_NOTE
    user = f"Question: {question}\n\nEvidence:\n{blocks}"
    return llm.call(system, user, config.temperature)
