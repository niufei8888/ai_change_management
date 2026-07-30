from pydantic import BaseModel, Field

from ask_luma import llm
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
    system = config.plan_prompt.format(tool_description=config.tool_description)
    return llm.call_structured(system, question, config.temperature, Plan)
