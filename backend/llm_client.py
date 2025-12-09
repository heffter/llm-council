"""High-level LLM client for making requests using provider abstraction."""

from typing import List, Dict, Any, Optional
from .providers import parse_provider_model, get_registry, Message, CompletionRequest
from .retry import with_retries
from .logger import get_logger

logger = get_logger()


async def query_model(
    model_id: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model using provider:model notation with retries.

    Args:
        model_id: Model identifier in format "provider:model" (e.g., "openai:gpt-4.1")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    try:
        # Parse provider:model notation
        parsed = parse_provider_model(model_id)

        # Get provider client
        registry = get_registry()
        client = registry.get_client(parsed.provider)

        # Convert messages to Message objects
        msg_objects = [Message(role=m['role'], content=m['content']) for m in messages]

        # Create request
        request = CompletionRequest(
            model=parsed.model,
            messages=msg_objects,
            timeout=timeout
        )

        logger.info("LLM request start", provider=parsed.provider, model=parsed.model, timeout=timeout)

        # Execute request with retries
        async def make_request():
            return await client.complete(request)

        response = await with_retries(make_request, retries=2, base_delay_ms=1000)

        logger.info("LLM request complete", provider=parsed.provider, model=parsed.model)

        return {
            'content': response.content,
            'reasoning_details': response.reasoning_details
        }

    except Exception as e:
        logger.error("LLM request failed", provider=parsed.provider if 'parsed' in locals() else 'unknown',
                    model=model_id, error=str(e))
        return None


async def query_models_parallel(
    model_ids: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel using provider:model notation.

    Args:
        model_ids: List of model identifiers in format "provider:model"
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model_id, messages) for model_id in model_ids]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model_id: response for model_id, response in zip(model_ids, responses)}
