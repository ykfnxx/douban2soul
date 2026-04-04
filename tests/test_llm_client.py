"""Tests for LLM client factory, OpenAI-compatible provider, and profiler."""

from unittest.mock import MagicMock, patch

import pytest

from douban2soul.analysis.llm_client import (
    AnalysisConfig,
    BaseLLMClient,
    LLMClientFactory,
    OpenAICompatClient,
)
from douban2soul.analysis.profiler import ProfileAnalyzer


class TestAnalysisConfig:

    def test_default_values(self):
        config = AnalysisConfig()
        assert config.llm_provider == "moonshot"
        assert config.base_url is None
        assert config.temperature == 0.7
        assert config.max_tokens == 4000

    def test_custom_values(self):
        config = AnalysisConfig(
            llm_provider="openai-compat",
            base_url="https://example.com/v1",
            model="my-model",
        )
        assert config.llm_provider == "openai-compat"
        assert config.base_url == "https://example.com/v1"
        assert config.model == "my-model"


class TestLLMClientFactory:

    def test_known_providers(self):
        expected = {"openai", "moonshot", "dashscope", "deepseek", "openai-compat"}
        assert set(LLMClientFactory.PROVIDERS.keys()) == expected

    def test_unknown_provider_raises(self):
        config = AnalysisConfig(llm_provider="nonexistent")
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClientFactory.create(config)


class TestOpenAICompatClient:

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises(self):
        config = AnalysisConfig(
            llm_provider="openai-compat",
            base_url="https://example.com/v1",
        )
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            OpenAICompatClient(config)

    @patch.dict("os.environ", {"LLM_API_KEY": "test-key"}, clear=True)
    def test_missing_base_url_raises(self):
        config = AnalysisConfig(llm_provider="openai-compat")
        with pytest.raises(ValueError, match="LLM_BASE_URL"):
            OpenAICompatClient(config)

    @patch("douban2soul.analysis.llm_client.OpenAICompatClient.__init__", return_value=None)
    def test_factory_creates_compat_client(self, mock_init):
        config = AnalysisConfig(llm_provider="openai-compat")
        client = LLMClientFactory.create(config)
        assert isinstance(client, OpenAICompatClient)

    @patch.dict("os.environ", {
        "LLM_API_KEY": "test-key",
        "LLM_BASE_URL": "https://example.com/v1",
        "LLM_MODEL": "custom-model",
    })
    @patch("douban2soul.analysis.llm_client.OpenAI")
    def test_env_vars_used(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        config = AnalysisConfig(llm_provider="openai-compat")
        client = OpenAICompatClient(config)
        mock_openai_cls.assert_called_once_with(
            api_key="test-key", base_url="https://example.com/v1"
        )
        assert client.model == "custom-model"

    @patch.dict("os.environ", {
        "LLM_API_KEY": "env-key",
        "LLM_BASE_URL": "https://env.com/v1",
    })
    @patch("douban2soul.analysis.llm_client.OpenAI")
    def test_config_overrides_env(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        config = AnalysisConfig(
            llm_provider="openai-compat",
            api_key="config-key",
            base_url="https://config.com/v1",
            model="config-model",
        )
        client = OpenAICompatClient(config)
        mock_openai_cls.assert_called_once_with(
            api_key="config-key", base_url="https://config.com/v1"
        )
        assert client.model == "config-model"

    @patch.dict("os.environ", {
        "LLM_API_KEY": "test-key",
        "LLM_BASE_URL": "https://example.com/v1",
    })
    @patch("douban2soul.analysis.llm_client.OpenAI")
    def test_default_model(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        config = AnalysisConfig(llm_provider="openai-compat")
        client = OpenAICompatClient(config)
        assert client.model == "gpt-3.5-turbo"

    @patch.dict("os.environ", {
        "LLM_API_KEY": "test-key",
        "LLM_BASE_URL": "https://example.com/v1",
    })
    @patch("douban2soul.analysis.llm_client.OpenAI")
    def test_complete_calls_api(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "test response"
        mock_client.chat.completions.create.return_value = mock_resp

        config = AnalysisConfig(llm_provider="openai-compat")
        client = OpenAICompatClient(config)
        result = client.complete("hello")

        assert result == "test response"
        mock_client.chat.completions.create.assert_called_once()

    @patch.dict("os.environ", {
        "LLM_API_KEY": "test-key",
        "LLM_BASE_URL": "https://example.com/v1",
    })
    @patch("douban2soul.analysis.llm_client.OpenAI")
    def test_stream_yields_chunks(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Build mock streaming response
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " world"
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None
        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])

        config = AnalysisConfig(llm_provider="openai-compat")
        client = OpenAICompatClient(config)
        result = list(client.stream("hello"))

        assert result == ["Hello", " world"]
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["stream"] is True


class _FakeLLM(BaseLLMClient):
    def __init__(self):
        super().__init__(AnalysisConfig())

    def complete(self, prompt: str) -> str:
        return "fake response"

    def stream(self, prompt):
        yield "chunk1"
        yield "chunk2"


class TestProfileAnalyzer:

    _RECORD = [{"title": "Test Movie", "myComment": "Great film", "myRating": 8}]

    def test_non_stream_does_not_recurse(self):
        profiler = ProfileAnalyzer(_FakeLLM(), stream=False)
        result = profiler.generate_comment_analysis(self._RECORD)
        assert "fake response" in result

    def test_stream_collects_chunks(self, capsys):
        profiler = ProfileAnalyzer(_FakeLLM(), stream=True)
        result = profiler.generate_comment_analysis(self._RECORD)
        assert "chunk1chunk2" in result
        captured = capsys.readouterr()
        assert "chunk1" in captured.out
        assert "chunk2" in captured.out
