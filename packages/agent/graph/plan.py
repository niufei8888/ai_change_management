from pydantic import BaseModel, Field

from agent import llm, tools
from behavior_core.config import BehaviorConfig


class Plan(BaseModel):
    in_scope: bool
    refusal_reason: str | None = None
    needs_search: bool = Field(
        description="Whether the documentation search tool should be used for this question."
    )
    query: str | None = None


def run(question: str, config: BehaviorConfig) -> tuple[Plan, llm.LLMResult]:
    """Scope guard, search decision, and first query -- one LLM call.

    needs_search is a real decision the model gets to make, not a formality.
    If the orchestrator searched unconditionally, narrowing tool_description
    could never stop retrieval happening, and the regression that whole demo
    rests on would be impossible to produce.
    """
    system = tools.expand_tools(config.plan_prompt, config)
    return llm.call_structured(system, question, Plan)
