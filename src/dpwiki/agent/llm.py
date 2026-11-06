"""Thin model client. Normalizes responses to plain dicts so tests can script a fake model."""

from __future__ import annotations

import os
from typing import Any, Protocol

from ..config import ModelConfig


class LLM(Protocol):
    def create(
        self,
        *,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_choice: dict | None = None,
        max_tokens: int = 8000,
    ) -> dict:
        """Return {"content": [blocks...], "stop_reason": str}.

        Blocks are {"type": "text", "text": ...} or
        {"type": "tool_use", "id": ..., "name": ..., "input": {...}}.
        """
        ...


class AnthropicLLM:
    def __init__(self, cfg: ModelConfig):
        self.model = cfg.id
        if cfg.provider == "bedrock":
            from anthropic import AnthropicBedrock

            self.client = AnthropicBedrock(aws_region=os.environ.get("AWS_REGION", "us-east-1"))
        elif cfg.provider == "anthropic":
            from anthropic import Anthropic

            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            self.client = Anthropic()
        else:
            raise ValueError(f"unknown model provider: {cfg.provider}")

    def create(self, *, system, messages, tools, tool_choice=None, max_tokens=8000) -> dict:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        resp = self.client.messages.create(**kwargs)
        blocks = []
        for b in resp.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        return {"content": blocks, "stop_reason": resp.stop_reason}


def make_llm(cfg: ModelConfig) -> LLM:
    return AnthropicLLM(cfg)
