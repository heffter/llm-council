"""OpenAI provider client."""

import httpx
from typing import Optional
from .base import LLMProviderClient, CompletionRequest, CompletionResponse


class OpenAIProvider(LLMProviderClient):
    """OpenAI API client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_ms: int = 120000
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            base_url: API base URL (defaults to OpenAI's endpoint)
            timeout_ms: Timeout in milliseconds
        """
        super().__init__(api_key, base_url, timeout_ms)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using OpenAI API.

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content

        Raises:
            httpx.HTTPError: On API errors
            Exception: On other failures
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
                    reasoning_details=message.get('reasoning_details')
                )

        except httpx.HTTPError as e:
            raise Exception(f"OpenAI API error: {e}")
        except Exception as e:
            raise Exception(f"OpenAI completion failed: {e}")
