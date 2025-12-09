"""Unit tests for providers/registry module."""

import pytest
import os
from backend.providers.registry import ProviderRegistry, ProviderConfig, get_registry
from backend.providers.parser import ParsedModelId


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_creation(self):
        """ProviderConfig should be creatable with required fields."""
        config = ProviderConfig(
            api_key="test-key",
            base_url="https://api.test.com",
            timeout_ms=30000
        )

        assert config.api_key == "test-key"
        assert config.base_url == "https://api.test.com"
        assert config.timeout_ms == 30000


class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    @pytest.fixture(autouse=True)
    def clean_env(self, monkeypatch):
        """Clear all provider-related environment variables before each test."""
        provider_env_vars = [
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
            "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
            "GOOGLE_API_KEY", "GEMINI_BASE_URL",
            "PERPLEXITY_API_KEY", "PERPLEXITY_BASE_URL",
            "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL",
        ]
        for var in provider_env_vars:
            monkeypatch.delenv(var, raising=False)

    @pytest.fixture
    def clean_registry(self):
        """Create a fresh registry for each test."""
        return ProviderRegistry()

    @pytest.fixture
    def mock_env_openai(self, monkeypatch):
        """Set up OpenAI environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    @pytest.fixture
    def mock_env_anthropic(self, monkeypatch):
        """Set up Anthropic environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

    def test_register_from_env_openai(self, clean_registry, mock_env_openai):
        """Should register OpenAI provider from environment."""
        clean_registry.register_from_env()

        assert clean_registry.is_provider_configured("openai")
        config = clean_registry.get_config("openai")
        assert config.api_key == "sk-test-openai-key"
        assert config.base_url == "https://api.openai.com/v1"

    def test_register_from_env_anthropic(self, clean_registry, mock_env_anthropic):
        """Should register Anthropic provider from environment."""
        clean_registry.register_from_env()

        assert clean_registry.is_provider_configured("anthropic")
        config = clean_registry.get_config("anthropic")
        assert config.api_key == "sk-ant-test-key"

    def test_register_from_env_no_keys(self, clean_registry):
        """Should not register providers without API keys."""
        # clean_env fixture already clears all provider env vars
        clean_registry.register_from_env()

        assert not clean_registry.is_provider_configured("openai")
        assert not clean_registry.is_provider_configured("anthropic")
        assert not clean_registry.is_provider_configured("gemini")
        assert not clean_registry.is_provider_configured("perplexity")
        assert not clean_registry.is_provider_configured("openrouter")

    def test_get_config_nonexistent_provider(self, clean_registry):
        """Should return None for unconfigured provider."""
        config = clean_registry.get_config("nonexistent")
        assert config is None

    def test_is_provider_configured_false(self, clean_registry):
        """Should return False for unconfigured provider."""
        assert not clean_registry.is_provider_configured("openai")

    def test_get_client_creates_instance(self, clean_registry, mock_env_openai):
        """Should create client instance for configured provider."""
        clean_registry.register_from_env()

        client = clean_registry.get_client("openai")

        assert client is not None
        assert hasattr(client, 'complete')

    def test_get_client_caching(self, clean_registry, mock_env_openai):
        """Should cache and reuse client instances."""
        clean_registry.register_from_env()

        client1 = clean_registry.get_client("openai")
        client2 = clean_registry.get_client("openai")

        # Should be the same instance
        assert client1 is client2

    def test_get_client_unconfigured_raises_error(self, clean_registry):
        """Should raise ValueError for unconfigured provider."""
        with pytest.raises(ValueError, match="Provider .* is not configured"):
            clean_registry.get_client("openai")

    def test_validate_model_id_configured_provider(self, clean_registry, mock_env_openai):
        """Should validate model ID when provider is configured."""
        clean_registry.register_from_env()

        # Should not raise
        clean_registry.validate_model_id("openai:gpt-4o")

    def test_validate_model_id_unconfigured_raises_error(self, clean_registry):
        """Should raise ValueError when provider not configured."""
        with pytest.raises(ValueError, match="Provider .* not configured"):
            clean_registry.validate_model_id("openai:gpt-4o")

    def test_validate_model_id_invalid_format_raises_error(self, clean_registry):
        """Should raise ValueError for invalid model ID format."""
        with pytest.raises(ValueError):
            clean_registry.validate_model_id("invalid-format")

    def test_multiple_providers_configured(self, clean_registry, monkeypatch):
        """Should handle multiple providers configured simultaneously."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

        clean_registry.register_from_env()

        assert clean_registry.is_provider_configured("openai")
        assert clean_registry.is_provider_configured("anthropic")
        assert clean_registry.is_provider_configured("gemini")
        assert not clean_registry.is_provider_configured("perplexity")

    def test_custom_base_url_respected(self, clean_registry, monkeypatch):
        """Should use custom base URL when provided."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.openai.com/v2")

        clean_registry.register_from_env()

        config = clean_registry.get_config("openai")
        assert config.base_url == "https://custom.openai.com/v2"

    def test_default_base_url_used(self, clean_registry, monkeypatch):
        """Should use default base URL when custom not provided."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

        clean_registry.register_from_env()

        config = clean_registry.get_config("openai")
        assert config.base_url == "https://api.openai.com/v1"

    def test_gemini_uses_google_api_key(self, clean_registry, monkeypatch):
        """Should use GOOGLE_API_KEY for Gemini provider."""
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key-123")

        clean_registry.register_from_env()

        assert clean_registry.is_provider_configured("gemini")
        config = clean_registry.get_config("gemini")
        assert config.api_key == "google-key-123"


class TestGetRegistry:
    """Tests for get_registry singleton function."""

    def test_returns_registry_instance(self):
        """Should return a ProviderRegistry instance."""
        registry = get_registry()
        assert isinstance(registry, ProviderRegistry)

    def test_singleton_behavior(self):
        """Should return the same instance on multiple calls."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_registry_auto_initialized(self, monkeypatch):
        """Registry should be initialized from environment on first call."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Get registry (triggers initialization)
        registry = get_registry()

        # Should have registered providers from environment
        assert registry.is_provider_configured("openai")
