#!/usr/bin/env python3
"""
Unified LLM Client Interface
Supports multiple providers: Moonshot, OpenAI, DashScope, DeepSeek
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnalysisConfig:
    """Analysis configuration"""
    llm_provider: str = "moonshot"
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000


class BaseLLMClient(ABC):
    """Base class for LLM clients"""

    def __init__(self, config: AnalysisConfig):
        self.config = config

    @abstractmethod
    def complete(self, prompt: str) -> str:
        pass


class MoonshotClient(BaseLLMClient):
    """Moonshot AI (Kimi) - Recommended"""

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install openai: pip install openai>=1.0.0")

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


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT"""

    def __init__(self, config: AnalysisConfig):
        super().__init__(config)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install openai: pip install openai>=1.0.0")

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
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install openai: pip install openai>=1.0.0")

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


class LLMClientFactory:
    """LLM client factory"""

    @staticmethod
    def create(config: AnalysisConfig) -> BaseLLMClient:
        """Create an LLM client for the specified provider"""
        if config.llm_provider == "openai":
            return OpenAIClient(config)
        elif config.llm_provider == "moonshot":
            return MoonshotClient(config)
        elif config.llm_provider == "dashscope":
            return DashScopeClient(config)
        elif config.llm_provider == "deepseek":
            return DeepSeekClient(config)
        else:
            raise ValueError(f"Unknown provider: {config.llm_provider}")


if __name__ == "__main__":
    print("LLM Client Test")
    print("=" * 50)
    print("Supported LLM providers:")
    print("  - moonshot (Kimi, recommended)")
    print("  - openai (GPT-4)")
    print("  - dashscope (Tongyi Qianwen)")
    print("  - deepseek (DeepSeek)")
    print("=" * 50)
