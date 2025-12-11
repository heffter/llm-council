"""
MCP Server for LLM Council.

Exposes council deliberation features as MCP tools for integration
with Claude Code, Cursor, and other MCP-compatible clients.
"""

import asyncio
import sys
import os
from typing import Optional, List, Dict, Any
from uuid import uuid4

from mcp.server.fastmcp import FastMCP

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.council import run_full_council, get_effective_models
from backend.storage import (
    create_conversation,
    get_conversation,
    list_conversations,
    add_user_message,
    add_assistant_message,
    update_conversation_title,
    build_conversation_history,
)
from backend.config import (
    COUNCIL_MODELS,
    CHAIRMAN_MODEL,
    RESEARCH_MODEL,
    CONVERSATION_CONTEXT_STRATEGY,
    MAX_CONTEXT_EXCHANGES,
)
from backend.providers import (
    get_all_models,
    get_all_presets,
    get_preset,
    resolve_preset,
    get_model_info,
)


# Initialize MCP server
mcp = FastMCP(
    "LLM Council",
    instructions="A 3-stage deliberation system where multiple LLMs answer questions collaboratively",
)


# =============================================================================
# Tool Response Types
# =============================================================================

def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create a standardized success response."""
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(error_type: str, message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "success": False,
        "error_type": error_type,
        "error_message": message,
        "data": None
    }


# =============================================================================
# Council Query Tools
# =============================================================================

@mcp.tool()
async def council_query(prompt: str) -> Dict[str, Any]:
    """
    Submit a query to the LLM Council for deliberation.

    The council uses a 3-stage process:
    1. Stage 1: All council models provide individual responses
    2. Stage 2: Each model ranks the anonymized responses
    3. Stage 3: Chairman synthesizes a final answer from all inputs

    This uses the default model configuration from environment variables.

    Args:
        prompt: The question or prompt to send to the council

    Returns:
        Dict containing:
        - stage1: Individual model responses
        - stage2: Peer rankings (anonymized)
        - stage3: Chairman's synthesized final answer
        - metadata: Label mappings and aggregate rankings
    """
    if not prompt or not prompt.strip():
        return error_response("validation_error", "Prompt cannot be empty")

    try:
        stage1, stage2, stage3, metadata = await run_full_council(
            user_query=prompt.strip(),
            conversation_history=None,
            model_config=None
        )

        return success_response({
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "metadata": metadata
        }, "Council deliberation complete")

    except Exception as e:
        return error_response("council_error", f"Council query failed: {str(e)}")


@mcp.tool()
async def council_query_with_models(
    prompt: str,
    council_models: Optional[List[str]] = None,
    chairman_model: Optional[str] = None,
    research_model: Optional[str] = None,
    preset: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a query to the LLM Council with custom model configuration.

    You can either specify individual models or use a preset.
    If preset is specified, it takes precedence over individual model settings.

    Available presets:
    - "fast": Quick responses with cost-efficient models
    - "balanced": Good balance of quality, speed, and cost
    - "comprehensive": Maximum quality with top-tier models

    Model IDs use provider:model format, e.g.:
    - "openai:gpt-4o"
    - "anthropic:claude-3-5-sonnet-latest"
    - "gemini:gemini-2.0-flash"

    Args:
        prompt: The question or prompt to send to the council
        council_models: List of model IDs for council members (provider:model format)
        chairman_model: Model ID for the chairman (provider:model format)
        research_model: Optional model ID for research/auxiliary tasks
        preset: Use a predefined model configuration (fast, balanced, comprehensive)

    Returns:
        Dict containing stage1, stage2, stage3 results and metadata
    """
    if not prompt or not prompt.strip():
        return error_response("validation_error", "Prompt cannot be empty")

    # Build model config
    model_config = None

    if preset:
        resolved = resolve_preset(preset)
        if resolved is None:
            return error_response(
                "validation_error",
                f"Unknown preset: {preset}. Available: fast, balanced, comprehensive"
            )
        model_config = resolved
    elif council_models or chairman_model or research_model:
        model_config = {}
        if council_models:
            model_config["council_models"] = council_models
        if chairman_model:
            model_config["chairman_model"] = chairman_model
        if research_model:
            model_config["research_model"] = research_model

    try:
        stage1, stage2, stage3, metadata = await run_full_council(
            user_query=prompt.strip(),
            conversation_history=None,
            model_config=model_config
        )

        # Get effective models used
        effective_council, effective_chairman, effective_research = get_effective_models(model_config)

        return success_response({
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "metadata": metadata,
            "models_used": {
                "council": effective_council,
                "chairman": effective_chairman,
                "research": effective_research
            }
        }, "Council deliberation complete")

    except Exception as e:
        return error_response("council_error", f"Council query failed: {str(e)}")


# =============================================================================
# Conversation Management Tools
# =============================================================================

@mcp.tool()
async def create_council_conversation(
    preset: Optional[str] = None,
    council_models: Optional[List[str]] = None,
    chairman_model: Optional[str] = None,
    research_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new conversation with the LLM Council.

    Conversations preserve context across multiple queries, allowing
    follow-up questions and continuity in the council's responses.

    Args:
        preset: Optional preset configuration (fast, balanced, comprehensive)
        council_models: Optional list of council model IDs
        chairman_model: Optional chairman model ID
        research_model: Optional research model ID

    Returns:
        Dict containing the new conversation ID and configuration
    """
    # Build model config
    model_config = None

    if preset:
        resolved = resolve_preset(preset)
        if resolved is None:
            return error_response(
                "validation_error",
                f"Unknown preset: {preset}. Available: fast, balanced, comprehensive"
            )
        model_config = {"preset": preset, **resolved}
    elif council_models or chairman_model or research_model:
        model_config = {}
        if council_models:
            model_config["council_models"] = council_models
        if chairman_model:
            model_config["chairman_model"] = chairman_model
        if research_model:
            model_config["research_model"] = research_model

    try:
        conversation_id = str(uuid4())
        conversation = create_conversation(conversation_id, model_config)

        return success_response({
            "conversation_id": conversation["id"],
            "created_at": conversation["created_at"],
            "title": conversation["title"],
            "model_config": model_config
        }, "Conversation created")

    except Exception as e:
        return error_response("storage_error", f"Failed to create conversation: {str(e)}")


@mcp.tool()
async def continue_conversation(
    conversation_id: str,
    prompt: str
) -> Dict[str, Any]:
    """
    Continue an existing council conversation with a follow-up query.

    This maintains conversation context, allowing the council to reference
    previous exchanges when generating responses.

    Args:
        conversation_id: The UUID of the conversation to continue
        prompt: The follow-up question or prompt

    Returns:
        Dict containing the council's response with all stages
    """
    if not conversation_id or not conversation_id.strip():
        return error_response("validation_error", "Conversation ID is required")

    if not prompt or not prompt.strip():
        return error_response("validation_error", "Prompt cannot be empty")

    try:
        # Load conversation
        conversation = get_conversation(conversation_id.strip())
        if conversation is None:
            return error_response("not_found", f"Conversation not found: {conversation_id}")

        # Get model config from conversation
        model_config = conversation.get("model_config")

        # Build conversation history
        history = build_conversation_history(
            conversation_id,
            strategy=CONVERSATION_CONTEXT_STRATEGY,
            max_exchanges=MAX_CONTEXT_EXCHANGES
        )

        # Save user message
        add_user_message(conversation_id, prompt.strip())

        # Run council with history
        stage1, stage2, stage3, metadata = await run_full_council(
            user_query=prompt.strip(),
            conversation_history=history,
            model_config=model_config
        )

        # Save assistant response
        add_assistant_message(conversation_id, stage1, stage2, stage3)

        return success_response({
            "conversation_id": conversation_id,
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "metadata": metadata,
            "message_count": len(conversation.get("messages", [])) + 2
        }, "Council response added to conversation")

    except Exception as e:
        return error_response("council_error", f"Failed to continue conversation: {str(e)}")


@mcp.tool()
async def get_council_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Retrieve a council conversation with all its messages.

    Args:
        conversation_id: The UUID of the conversation to retrieve

    Returns:
        Dict containing the full conversation including all messages
    """
    if not conversation_id or not conversation_id.strip():
        return error_response("validation_error", "Conversation ID is required")

    try:
        conversation = get_conversation(conversation_id.strip())
        if conversation is None:
            return error_response("not_found", f"Conversation not found: {conversation_id}")

        return success_response({
            "id": conversation["id"],
            "created_at": conversation["created_at"],
            "title": conversation.get("title", "New Conversation"),
            "model_config": conversation.get("model_config"),
            "messages": conversation.get("messages", []),
            "message_count": len(conversation.get("messages", []))
        })

    except Exception as e:
        return error_response("storage_error", f"Failed to retrieve conversation: {str(e)}")


@mcp.tool()
async def list_council_conversations(
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List all council conversations with pagination.

    Returns conversation metadata (ID, title, message count) without
    the full message contents.

    Args:
        limit: Maximum number of conversations to return (default: 20, max: 100)
        offset: Number of conversations to skip for pagination (default: 0)

    Returns:
        Dict containing list of conversation metadata
    """
    # Validate pagination params
    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    if offset < 0:
        offset = 0

    try:
        all_conversations = list_conversations()
        total_count = len(all_conversations)

        # Apply pagination
        paginated = all_conversations[offset:offset + limit]

        return success_response({
            "conversations": paginated,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        })

    except Exception as e:
        return error_response("storage_error", f"Failed to list conversations: {str(e)}")


# =============================================================================
# Configuration Tools
# =============================================================================

@mcp.tool()
async def get_current_config() -> Dict[str, Any]:
    """
    Get the current council configuration.

    Returns the models currently configured for council deliberations,
    including council members, chairman, and optional research model.

    Returns:
        Dict containing current model configuration
    """
    return success_response({
        "council_models": COUNCIL_MODELS,
        "chairman_model": CHAIRMAN_MODEL,
        "research_model": RESEARCH_MODEL,
        "context_strategy": CONVERSATION_CONTEXT_STRATEGY,
        "max_context_exchanges": MAX_CONTEXT_EXCHANGES
    })


@mcp.tool()
async def list_available_models() -> Dict[str, Any]:
    """
    List all available models in the catalog.

    Returns models with their metadata including cost tier, speed tier,
    and context window information.

    Returns:
        Dict containing list of available models
    """
    try:
        models = get_all_models()
        model_list = [
            {
                "id": m.full_id,
                "provider": m.provider,
                "display_name": m.display_name,
                "cost_tier": m.cost_tier,
                "speed_tier": m.speed_tier,
                "description": m.description,
                "context_window": m.context_window
            }
            for m in models
        ]

        return success_response({
            "models": model_list,
            "count": len(model_list)
        })

    except Exception as e:
        return error_response("catalog_error", f"Failed to list models: {str(e)}")


@mcp.tool()
async def list_presets() -> Dict[str, Any]:
    """
    List available model presets.

    Presets are pre-configured combinations of council, chairman, and
    research models optimized for different use cases.

    Returns:
        Dict containing available preset configurations
    """
    try:
        presets = get_all_presets()
        preset_list = [
            {
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "council_models": p.council_models,
                "chairman_model": p.chairman_model,
                "research_model": p.research_model
            }
            for p in presets
        ]

        return success_response({
            "presets": preset_list,
            "count": len(preset_list)
        })

    except Exception as e:
        return error_response("catalog_error", f"Failed to list presets: {str(e)}")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
