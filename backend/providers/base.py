"""Base provider abstraction for LLM clients."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class Message:
    """A chat message."""
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class CompletionRequest:
    """Request parameters for LLM completion."""
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0


@dataclass
class CompletionResponse:
    """Response from LLM completion."""
    content: str
    reasoning_details: Any = None


class LLMProviderClient(ABC):
    """Abstract base class for LLM provider clients."""

    def __init__(self, api_key: str, base_url: str, timeout_ms: int = 120000):
        """
        Initialize provider client.

        Args:
            api_key: API key for the provider
            base_url: Base URL for API requests
            timeout_ms: Default timeout in milliseconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_ms = timeout_ms

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate a completion from the LLM.

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content

        Raises:
            Exception: On API errors, timeouts, or invalid responses
        """
        pass

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert Message objects to dict format for API calls."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
