"""Google Gemini provider client."""

import httpx
from .base import LLMProviderClient, CompletionRequest, CompletionResponse


class GeminiProvider(LLMProviderClient):
    """Google Gemini API client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_ms: int = 120000
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key
            base_url: API base URL (defaults to Google's Gemini endpoint)
            timeout_ms: Timeout in milliseconds
        """
        super().__init__(api_key, base_url, timeout_ms)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using Gemini API.

        Args:
            request: Completion request parameters

        Returns:
            CompletionResponse with generated content

        Raises:
            Exception: On API errors or other failures
        """
        # Convert messages to Gemini format
        contents = []
        for msg in request.messages:
            # Map roles: system/user -> user, assistant -> model
            role = "user" if msg.role in ["system", "user"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            }
        }

        timeout = request.timeout if request.timeout > 0 else (self.timeout_ms / 1000.0)

        # Gemini uses API key as query parameter
        url = f"{self.base_url}/models/{request.model}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                response.raise_for_status()

                data = response.json()

                # Extract content from Gemini response
                content = ''
                candidates = data.get('candidates', [])
                if candidates:
                    candidate = candidates[0]
                    content_parts = candidate.get('content', {}).get('parts', [])
                    if content_parts:
                        content = ''.join([
                            part.get('text', '')
                            for part in content_parts
                        ])

                return CompletionResponse(
                    content=content,
                    reasoning_details=None
                )

        except httpx.HTTPError as e:
            raise Exception(f"Gemini API error: {e}")
        except Exception as e:
            raise Exception(f"Gemini completion failed: {e}")
