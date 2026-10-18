"""Demonstrates the fact-checker end to end without calling the real AI.

A stand-in model first drafts a reply with a WRONG price; the fact-checker blocks it and sends the
problem back; the stand-in then corrects it. Run from the backend folder:
    python factcheck_demo.py
"""

import json

from pydantic_ai.messages import ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from agent import dan
from models import ShopDeps

drafts = []


def unreliable_model(messages, info: AgentInfo) -> ModelResponse:
    output_tool = info.output_tools[0].name
    retry = [p for m in messages for p in getattr(m, "parts", []) if isinstance(p, RetryPromptPart)]
    if not retry:
        reply = "The Basic Hoodie Big Yale is $55, a steal for The Game."  # wrong: it's $68
    else:
        print("\nFact-checker sent back:\n ", retry[-1].content if isinstance(retry[-1].content, str) else retry[-1].content)
        reply = "The Basic Hoodie Big Yale is $68, a steal for The Game."
    drafts.append(reply)
    args = {"reply": reply, "product_ids": ["basic-hoodie-big-yale"]}
    return ModelResponse(parts=[ToolCallPart(output_tool, json.dumps(args))])


if __name__ == "__main__":
    deps = ShopDeps()
    with dan.override(model=FunctionModel(unreliable_model)):
        result = dan.run_sync("How much is the Basic Hoodie Big Yale?", deps=deps)
    print("\nDraft 1 (blocked):", drafts[0])
    print("Draft 2 (sent):   ", result.output.reply)
    print(f"Corrections: {deps.corrections}, facts checked in final reply: {deps.facts_checked}")
