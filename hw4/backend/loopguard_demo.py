"""Demonstrates Handsome Dan's loop protection without calling the real AI.

Three deliberately misbehaving stand-in models:
  1. calls the same tool with the same inputs forever  -> stopped as "repeated_tool_call"
  2. keeps calling tools with new inputs forever       -> stopped as "tool_call_limit"
     (one tool per AI call would hit the 8-AI-call limit first, so it asks for two at a time)
  3. takes too long to answer                          -> stopped as "timeout_1_minute"
Each run is written to output/audit_trail.json, labeled as a test. Run from the backend folder:
    python loopguard_demo.py
"""

import asyncio
import itertools

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import agent
import audit
from agent import ask_dan, dan, get_conversation
from models import ShopDeps

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
PRODUCTS = ["yale-dad-hoodie", "basic-hoodie-big-yale", "brooks-brothers-bomber-jacket-yale"]


def stuck_model(messages, info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("check_stock", {"product_id": "yale-dad-hoodie", "size": "M"})])


_wander = itertools.cycle([(p, s) for p in PRODUCTS for s in SIZES])


def wandering_model(messages, info: AgentInfo) -> ModelResponse:
    """Asks for two new stock checks at a time, forever."""
    parts = []
    for _ in range(2):
        product, size = next(_wander)
        parts.append(ToolCallPart("check_stock", {"product_id": product, "size": size}))
    return ModelResponse(parts=parts)


async def slow_model(messages, info: AgentInfo) -> ModelResponse:
    await asyncio.sleep(3)
    return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie"})])


async def main() -> None:
    original_append = audit.append
    audit.append = lambda record: original_append({**record, "note": "loop-guard test (stand-in model)"})
    try:
        for label, model, timeout in [
            ("1. stuck in a loop", FunctionModel(stuck_model), 60),
            ("2. wandering forever", FunctionModel(wandering_model), 60),
            ("3. too slow", FunctionModel(slow_model), 1),
        ]:
            agent.RUN_TIMEOUT_SECONDS = timeout  # the 1-minute limit, shortened so the demo is quick
            cid, conv = get_conversation(None, None)
            deps = ShopDeps()
            with dan.override(model=model):
                reply = await ask_dan(conv, "test question", deps, cid)
            calls = [f"{c['tool']}({', '.join(c['args'].values())}) -> {c.get('result', '')}" for c in deps.tool_log]
            print(f"\n{label}: {len(calls)} tool call(s)")
            for c in calls[-3:]:
                print("   ", c)
            print("    shopper sees:", reply.reply)
    finally:
        audit.append = original_append
        agent.RUN_TIMEOUT_SECONDS = 60


if __name__ == "__main__":
    asyncio.run(main())
