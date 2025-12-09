"""Provider:model notation parser."""

from typing import Literal
from dataclasses import dataclass


ProviderId = Literal['openai', 'anthropic', 'gemini', 'perplexity', 'openrouter']

SUPPORTED_PROVIDERS = {'openai', 'anthropic', 'gemini', 'perplexity', 'openrouter'}


@dataclass
class ParsedModelId:
    """Parsed provider and model identifier."""
    provider: ProviderId
    model: str


def parse_provider_model(model_id: str) -> ParsedModelId:
    """
    Parse a provider:model string into components.

    Args:
        model_id: String in format "provider:model" (e.g., "openai:gpt-4o")

    Returns:
        ParsedModelId with provider and model fields

    Raises:
        ValueError: If format is invalid or provider is unsupported

    Examples:
        >>> parse_provider_model("openai:gpt-4.1")
        ParsedModelId(provider='openai', model='gpt-4.1')

        >>> parse_provider_model("anthropic:claude-3-5-sonnet")
        ParsedModelId(provider='anthropic', model='claude-3-5-sonnet')
    """
    if ':' not in model_id:
        raise ValueError(f"Invalid provider:model string: {model_id}. Expected format: 'provider:model'")

    parts = model_id.split(':', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid provider:model string: {model_id}")

    provider, model = parts

    if not provider or not model:
        raise ValueError(f"Invalid provider:model string: {model_id}. Both provider and model must be non-empty")

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )

    return ParsedModelId(provider=provider, model=model)  # type: ignore
