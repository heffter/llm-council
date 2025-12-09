"""Anthropic provider client."""

import httpx
from .base import LLMProviderClient, CompletionRequest, CompletionResponse


class AnthropicProvider(LLMProviderClient):
    """Anthropic API client for Claude models."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        timeout_ms: int = 120000
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            base_url: API base URL (defaults to Anthropic's endpoint)
            timeout_ms: Timeout in milliseconds
        """
        super().__init__(api_key, base_url, timeout_ms)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using Anthropic API.

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content

        Raises:
            Exception: On API errors or other failures
        """
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Anthropic API requires system message separate from messages
        messages = self._convert_messages(request.messages)
        system_message = None

        # Extract system message if present
        if messages and messages[0]["role"] == "system":
            system_message = messages[0]["content"]
            messages = messages[1:]

        payload = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        if system_message:
            payload["system"] = system_message

        timeout = request.timeout if request.timeout > 0 else (self.timeout_ms / 1000.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()

                # Anthropic returns content as a list of content blocks
                content_blocks = data.get('content', [])
                content = ''
                if content_blocks:
                    # Join all text blocks
                    content = ''.join([
                        block.get('text', '')
                        for block in content_blocks
                        if block.get('type') == 'text'
                    ])

                return CompletionResponse(
                    content=content,
                    reasoning_details=None
                )

        except httpx.HTTPError as e:
            raise Exception(f"Anthropic API error: {e}")
        except Exception as e:
            raise Exception(f"Anthropic completion failed: {e}")
