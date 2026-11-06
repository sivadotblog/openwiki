"""A scripted model for tests, demos, and seeding without an API key.

It replays a fixed plan and fixed pages through the same tools the real model uses,
so the full lifecycle (plan, claim validation, finalize) runs for real.
"""

from __future__ import annotations

import itertools
from typing import Any

_ids = itertools.count(1)


def _use(name: str, inp: dict) -> dict:
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": inp}


class ScriptedLLM:
    """plan: submit_plan input. pages: path -> submit_page input. answers: list of ask replies."""

    def __init__(self, plan: dict, pages: dict[str, dict], answer: str = "scripted answer"):
        self.plan = plan
        self.pages = pages
        self.answer = answer
        self.calls: list[dict[str, Any]] = []

    def create(self, *, system, messages, tools, tool_choice=None, max_tokens=8000) -> dict:
        self.calls.append({"system": system, "messages": messages, "tools": [t["name"] for t in tools]})
        names = {t["name"] for t in tools}
        if "submit_plan" in names:
            return {"content": [_use("submit_plan", self.plan)], "stop_reason": "tool_use"}
        if "submit_page" in names:
            last = messages[-1]["content"]
            if isinstance(last, list) and any(
                isinstance(b, dict) and str(b.get("content", "")).startswith("error") for b in last
            ):
                raise RuntimeError(f"scripted page rejected: {last}")
            first = messages[0]["content"]
            path = next((p for p in self.pages if p in first), None)
            if path is None:
                raise RuntimeError(f"no scripted page for: {first}")
            spec = self.pages[path]
            if spec.get("delete"):
                return {
                    "content": [_use("delete_page", {"path": path, "reason": spec["delete"]})],
                    "stop_reason": "tool_use",
                }
            return {"content": [_use("submit_page", {"path": path, **spec})], "stop_reason": "tool_use"}
        # ask mode
        if len(messages) == 1:
            return {"content": [_use("search_wiki", {"query": messages[0]["content"]})], "stop_reason": "tool_use"}
        return {"content": [{"type": "text", "text": self.answer}], "stop_reason": "end_turn"}
