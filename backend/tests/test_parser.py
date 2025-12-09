"""Unit tests for providers/parser module."""

import pytest
from backend.providers.parser import (
    parse_provider_model,
    ParsedModelId,
    SUPPORTED_PROVIDERS
)
from backend.config import parse_model_list


class TestParseProviderModel:
    """Tests for parse_provider_model function."""

    def test_valid_openai_model(self):
        """Valid OpenAI provider:model string should parse correctly."""
        result = parse_provider_model("openai:gpt-4o")

        assert result.provider == "openai"
        assert result.model == "gpt-4o"

    def test_valid_anthropic_model(self):
        """Valid Anthropic provider:model string should parse correctly."""
        result = parse_provider_model("anthropic:claude-3-5-sonnet-latest")

        assert result.provider == "anthropic"
        assert result.model == "claude-3-5-sonnet-latest"

    def test_valid_gemini_model(self):
        """Valid Gemini provider:model string should parse correctly."""
        result = parse_provider_model("gemini:gemini-2.0-pro")

        assert result.provider == "gemini"
        assert result.model == "gemini-2.0-pro"

    def test_valid_perplexity_model(self):
        """Valid Perplexity provider:model string should parse correctly."""
        result = parse_provider_model("perplexity:sonar-pro")

        assert result.provider == "perplexity"
        assert result.model == "sonar-pro"

    def test_valid_openrouter_model(self):
        """Valid OpenRouter provider:model string should parse correctly."""
        result = parse_provider_model("openrouter:anthropic/claude-3-5-sonnet")

        assert result.provider == "openrouter"
        assert result.model == "anthropic/claude-3-5-sonnet"

    def test_missing_colon_raises_error(self):
        """String without colon should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid provider:model string"):
            parse_provider_model("gpt-4o")

    def test_empty_provider_raises_error(self):
        """Empty provider name should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid provider:model string"):
            parse_provider_model(":gpt-4o")

    def test_empty_model_raises_error(self):
        """Empty model name should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid provider:model string"):
            parse_provider_model("openai:")

    def test_unsupported_provider_raises_error(self):
        """Unsupported provider should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            parse_provider_model("unknown:model-name")

    def test_multiple_colons_handled(self):
        """Model names with colons should work (everything after first colon is model)."""
        result = parse_provider_model("openrouter:openai:gpt-4o")

        assert result.provider == "openrouter"
        assert result.model == "openai:gpt-4o"

    def test_case_sensitive_provider(self):
        """Provider names should be case-sensitive."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            parse_provider_model("OpenAI:gpt-4o")

    def test_all_supported_providers_listed(self):
        """All expected providers should be in SUPPORTED_PROVIDERS."""
        expected = ["openai", "anthropic", "gemini", "perplexity", "openrouter"]
        assert set(SUPPORTED_PROVIDERS) == set(expected)


class TestParseModelList:
    """Tests for parse_model_list function."""

    def test_single_model(self):
        """Single model string should return list with one model ID string."""
        result = parse_model_list("openai:gpt-4o")

        assert len(result) == 1
        assert result[0] == "openai:gpt-4o"

    def test_multiple_models(self):
        """Comma-separated models should return list of model ID strings."""
        result = parse_model_list("openai:gpt-4o,anthropic:claude-3-5-sonnet-latest")

        assert len(result) == 2
        assert result[0] == "openai:gpt-4o"
        assert result[1] == "anthropic:claude-3-5-sonnet-latest"

    def test_whitespace_trimmed(self):
        """Whitespace around models should be trimmed."""
        result = parse_model_list(" openai:gpt-4o , anthropic:claude-3-5-sonnet-latest ")

        assert len(result) == 2
        assert result[0] == "openai:gpt-4o"
        assert result[1] == "anthropic:claude-3-5-sonnet-latest"

    def test_empty_string_returns_empty_list(self):
        """Empty string should return empty list."""
        result = parse_model_list("")
        assert result == []

    def test_empty_after_split_returns_empty_list(self):
        """String with only commas/whitespace should return empty list."""
        result = parse_model_list(" , , ")
        assert result == []

    def test_three_models(self):
        """Three comma-separated models should all parse correctly."""
        models_str = "openai:gpt-4o,anthropic:claude-3-5-sonnet-latest,gemini:gemini-2.0-pro"
        result = parse_model_list(models_str)

        assert len(result) == 3
        assert result[0] == "openai:gpt-4o"
        assert result[1] == "anthropic:claude-3-5-sonnet-latest"
        assert result[2] == "gemini:gemini-2.0-pro"

    def test_duplicate_models_allowed(self):
        """Duplicate models should be allowed (config validation happens elsewhere)."""
        result = parse_model_list("openai:gpt-4o,openai:gpt-4o")

        assert len(result) == 2
        assert result[0] == "openai:gpt-4o"
        assert result[1] == "openai:gpt-4o"

    def test_none_returns_empty_list(self):
        """None input should return empty list."""
        result = parse_model_list(None)
        assert result == []


class TestParsedModelId:
    """Tests for ParsedModelId dataclass."""

    def test_dataclass_creation(self):
        """ParsedModelId should be creatable with provider and model."""
        parsed = ParsedModelId(provider="openai", model="gpt-4o")

        assert parsed.provider == "openai"
        assert parsed.model == "gpt-4o"

    def test_equality(self):
        """Two ParsedModelId with same values should be equal."""
        parsed1 = ParsedModelId(provider="openai", model="gpt-4o")
        parsed2 = ParsedModelId(provider="openai", model="gpt-4o")

        assert parsed1 == parsed2

    def test_string_representation(self):
        """ParsedModelId should have readable string representation."""
        parsed = ParsedModelId(provider="openai", model="gpt-4o")
        str_repr = str(parsed)

        assert "openai" in str_repr
        assert "gpt-4o" in str_repr
