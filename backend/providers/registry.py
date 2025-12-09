"""Provider registry and factory."""

import os
from typing import Dict, Optional
from .base import LLMProviderClient
from .parser import ProviderId, parse_provider_model
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .perplexity_provider import PerplexityProvider
from .openrouter_provider import OpenRouterProvider


class ProviderConfig:
    """Configuration for a specific provider."""

    def __init__(self, api_key: str, base_url: str, timeout_ms: int = 120000):
        """
        Initialize provider configuration.

        Args:
            api_key: API key for the provider
            base_url: Base URL for API requests
            timeout_ms: Default timeout in milliseconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_ms = timeout_ms


class ProviderRegistry:
    """Registry for managing LLM provider clients."""

    def __init__(self):
        """Initialize empty provider registry."""
        self._configs: Dict[ProviderId, Optional[ProviderConfig]] = {}
        self._clients: Dict[ProviderId, Optional[LLMProviderClient]] = {}

    def register_from_env(self) -> None:
        """
        Load provider configurations from environment variables.

        Looks for API keys in env:
        - OPENAI_API_KEY
        - ANTHROPIC_API_KEY
        - GOOGLE_API_KEY
        - PERPLEXITY_API_KEY
        - OPENROUTER_API_KEY
        """
        # OpenAI
        if openai_key := os.getenv("OPENAI_API_KEY"):
            self._configs['openai'] = ProviderConfig(
                api_key=openai_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                timeout_ms=120000
            )

        # Anthropic
        if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
            self._configs['anthropic'] = ProviderConfig(
                api_key=anthropic_key,
                base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
                timeout_ms=120000
            )

        # Gemini (uses GOOGLE_API_KEY for Gemini/Vertex access)
        if gemini_key := os.getenv("GOOGLE_API_KEY"):
            self._configs['gemini'] = ProviderConfig(
                api_key=gemini_key,
                base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
                timeout_ms=120000
            )

        # Perplexity
        if perplexity_key := os.getenv("PERPLEXITY_API_KEY"):
            self._configs['perplexity'] = ProviderConfig(
                api_key=perplexity_key,
                base_url=os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai"),
                timeout_ms=120000
            )

        # OpenRouter
        if openrouter_key := os.getenv("OPENROUTER_API_KEY"):
            self._configs['openrouter'] = ProviderConfig(
                api_key=openrouter_key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                timeout_ms=120000
            )

    def get_client(self, provider: ProviderId) -> LLMProviderClient:
        """
        Get or create a client for the specified provider.

        Args:
            provider: Provider identifier

        Returns:
            LLMProviderClient instance

        Raises:
            ValueError: If provider is not configured
        """
        # Return cached client if available
        if provider in self._clients and self._clients[provider] is not None:
            return self._clients[provider]

        # Check if provider is configured
        config = self._configs.get(provider)
        if config is None:
            raise ValueError(
                f"Provider '{provider}' is not configured. "
                f"Please set {_env_var_for_provider(provider)} environment variable."
            )

        # Create new client based on provider type
        client: LLMProviderClient
        if provider == 'openai':
            client = OpenAIProvider(config.api_key, config.base_url, config.timeout_ms)
        elif provider == 'anthropic':
            client = AnthropicProvider(config.api_key, config.base_url, config.timeout_ms)
        elif provider == 'gemini':
            client = GeminiProvider(config.api_key, config.base_url, config.timeout_ms)
        elif provider == 'perplexity':
            client = PerplexityProvider(config.api_key, config.base_url, config.timeout_ms)
        elif provider == 'openrouter':
            client = OpenRouterProvider(config.api_key, config.base_url, config.timeout_ms)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Cache and return
        self._clients[provider] = client
        return client

    def is_provider_configured(self, provider: ProviderId) -> bool:
        """
        Check if a provider is configured with an API key.

        Args:
            provider: Provider identifier

        Returns:
            True if provider has a config, False otherwise
        """
        return provider in self._configs and self._configs[provider] is not None

    def get_config(self, provider: str) -> Optional[ProviderConfig]:
        """
        Get configuration for a specific provider.

        Args:
            provider: Provider identifier

        Returns:
            ProviderConfig if configured, None otherwise
        """
        return self._configs.get(provider)

    def validate_model_id(self, model_id: str) -> None:
        """
        Validate that a provider:model string is configured.

        Args:
            model_id: String in format "provider:model"

        Raises:
            ValueError: If format is invalid or provider not configured
        """
        parsed = parse_provider_model(model_id)
        if not self.is_provider_configured(parsed.provider):
            raise ValueError(
                f"Provider '{parsed.provider}' from model '{model_id}' is not configured. "
                f"Please set {_env_var_for_provider(parsed.provider)} environment variable."
            )


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry, initializing if needed."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _registry.register_from_env()
    return _registry


def _env_var_for_provider(provider: ProviderId) -> str:
    """Return the expected API key env var for a provider."""
    if provider == 'gemini':
        return "GOOGLE_API_KEY"
    return f"{provider.upper()}_API_KEY"
