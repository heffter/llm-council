"""Perplexity provider client."""

import httpx
from .base import LLMProviderClient, CompletionRequest, CompletionResponse


class PerplexityProvider(LLMProviderClient):
    """Perplexity API client (uses OpenAI-compatible format)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.perplexity.ai",
        timeout_ms: int = 120000
    ):
        """
        Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key
            base_url: API base URL (defaults to Perplexity's endpoint)
            timeout_ms: Timeout in milliseconds
        """
        super().__init__(api_key, base_url, timeout_ms)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using Perplexity API.

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content

        Raises:
            Exception: On API errors or other failures
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": request.model,
            "messages": self._convert_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        timeout = request.timeout if request.timeout > 0 else (self.timeout_ms / 1000.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()
                message = data['choices'][0]['message']

                return CompletionResponse(
                    content=message.get('content', ''),
                    reasoning_details=None
                )

        except httpx.HTTPError as e:
            raise Exception(f"Perplexity API error: {e}")
        except Exception as e:
            raise Exception(f"Perplexity completion failed: {e}")
