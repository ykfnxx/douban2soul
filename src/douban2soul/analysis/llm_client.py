#!/usr/bin/env python3
"""
Unified LLM Client Interface
Supports multiple providers: Moonshot, OpenAI, DashScope, DeepSeek,
and any OpenAI-compatible API via the ``openai-compat`` provider.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

from openai import OpenAI


@dataclass
class AnalysisConfig:
    """Analysis configuration"""
    llm_provider: str = "moonshot"
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    base_url: Optional[str] = None  # for openai-compat provider


class BaseLLMClient(ABC):
    """Base class for LLM clients"""

    def __init__(self, config: AnalysisConfig):
        self.config = config

    @abstractmethod
    def complete(self, prompt: str) -> str:
        pass

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield response chunks. Default: single chunk from complete()."""
        yield self.complete(prompt)


def _openai_stream(client, model: str, prompt: str, config: AnalysisConfig) -> Iterator[str]:
    """Shared streaming helper for OpenAI SDK-based clients."""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        stream=True,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content


class MoonshotClient(BaseLLMClient):
    """Moonshot AI (Kimi) - Recommended"""

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        api_key = config.api_key or os.getenv("MOONSHOT_API_KEY")
        if not api_key:
            raise ValueError("Please set the MOONSHOT_API_KEY environment variable")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1"
        )
        self.model = config.model or "moonshot-v1-128k"

    def complete(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return resp.choices[0].message.content

    def stream(self, prompt: str) -> Iterator[str]:
        return _openai_stream(self.client, self.model, prompt, self.config)


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT"""

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable")

        self.client = OpenAI(api_key=api_key)
        self.model = config.model or "gpt-4"

    def complete(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return resp.choices[0].message.content

    def stream(self, prompt: str) -> Iterator[str]:
        return _openai_stream(self.client, self.model, prompt, self.config)


class DashScopeClient(BaseLLMClient):
    """Alibaba Cloud Tongyi Qianwen"""

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        try:
            import dashscope
        except ImportError:
            raise ImportError("Please install dashscope: pip install dashscope")

        api_key = config.api_key or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("Please set the DASHSCOPE_API_KEY environment variable")

        dashscope.api_key = api_key
        self.model = config.model or "qwen-max"
        self.dashscope = dashscope

    def complete(self, prompt: str) -> str:
        from dashscope import Generation
        resp = Generation.call(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return resp.output.text


class DeepSeekClient(BaseLLMClient):
    """DeepSeek"""

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        api_key = config.api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("Please set the DEEPSEEK_API_KEY environment variable")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = config.model or "deepseek-chat"

    def complete(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return resp.choices[0].message.content

    def stream(self, prompt: str) -> Iterator[str]:
        return _openai_stream(self.client, self.model, prompt, self.config)


class OpenAICompatClient(BaseLLMClient):
    """
    Generic client for any OpenAI API-compatible provider.

    Configuration via environment variables or AnalysisConfig:
      - ``LLM_API_KEY`` / config.api_key   — API key (required)
      - ``LLM_BASE_URL`` / config.base_url — API base URL (required)
      - ``LLM_MODEL`` / config.model       — Model name (default: gpt-3.5-turbo)
    """

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        api_key = config.api_key or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "Please set the LLM_API_KEY environment variable "
                "for openai-compat provider"
            )

        base_url = config.base_url or os.getenv("LLM_BASE_URL")
        if not base_url:
            raise ValueError(
                "Please set the LLM_BASE_URL environment variable "
                "or pass --base-url for openai-compat provider"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = config.model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    def complete(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return resp.choices[0].message.content

    def stream(self, prompt: str) -> Iterator[str]:
        return _openai_stream(self.client, self.model, prompt, self.config)


class LLMClientFactory:
    """LLM client factory"""

    PROVIDERS = {
        "openai": OpenAIClient,
        "moonshot": MoonshotClient,
        "dashscope": DashScopeClient,
        "deepseek": DeepSeekClient,
        "openai-compat": OpenAICompatClient,
    }

    @staticmethod
    def create(config: AnalysisConfig) -> BaseLLMClient:
        """Create an LLM client for the specified provider"""
        client_cls = LLMClientFactory.PROVIDERS.get(config.llm_provider)
        if client_cls is None:
            raise ValueError(f"Unknown provider: {config.llm_provider}")
        return client_cls(config)
