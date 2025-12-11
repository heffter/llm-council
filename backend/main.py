"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .config import validate_config, CONVERSATION_CONTEXT_STRATEGY, MAX_CONTEXT_EXCHANGES
from .storage_utils import InvalidConversationIdError, PathTraversalError
from .middleware import shared_secret_middleware, rate_limit_middleware
from .logger import get_logger
from .routes.config import router as config_router
from .providers import get_preset, get_model_info, parse_provider_model
from .council_validation import validate_council_config, MIN_COUNCIL_SIZE, MAX_COUNCIL_SIZE
from .webhook import emit_webhook, WebhookEvent

app = FastAPI(title="LLM Council API")

# Register routers
app.include_router(config_router)


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup."""
    try:
        validate_config()
        print("Configuration validated successfully")
    except ValueError as e:
        print(f"FATAL: {e}")
        raise SystemExit(1)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication and rate limiting middleware
# Order matters: rate_limit runs first, then shared_secret
# Note: FastAPI middleware wraps in reverse order, so add shared_secret first
# to make rate_limit execute first (outermost)
app.middleware("http")(shared_secret_middleware)
app.middleware("http")(rate_limit_middleware)


class ModelConfigRequest(BaseModel):
    """Model configuration for a conversation."""
    preset: Optional[str] = None  # "fast", "balanced", "comprehensive"
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None
    research_model: Optional[str] = None
    webhook_url: Optional[str] = None  # Per-conversation webhook URL override

    @field_validator('preset')
    @classmethod
    def validate_preset(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_presets = ['fast', 'balanced', 'comprehensive']
            if v.lower() not in valid_presets:
                raise ValueError(f"Invalid preset: {v}. Must be one of: {', '.join(valid_presets)}")
            return v.lower()
        return v

    @field_validator('webhook_url')
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not v.startswith(('http://', 'https://')):
                raise ValueError("Webhook URL must start with http:// or https://")
        return v


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    model_config_data: Optional[ModelConfigRequest] = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]
    model_config_data: Optional[Dict[str, Any]] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


def validate_model_id(model_id: str) -> None:
    """
    Validate a provider:model string.

    Raises HTTPException if invalid.
    """
    try:
        parsed = parse_provider_model(model_id)
        # Model exists in catalog or is a valid custom model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid model ID: {model_id}. {str(e)}")


def resolve_model_config(config: Optional[ModelConfigRequest]) -> Optional[Dict[str, Any]]:
    """
    Resolve and validate model configuration.

    If a preset is specified, resolve it to concrete model IDs.
    If explicit models are specified, validate them.
    Validates council size constraints (min 2, max 7).

    Returns dict suitable for storage or None if no config.
    """
    if config is None:
        return None

    result: Dict[str, Any] = {}

    # If preset is specified, use it as the base
    if config.preset:
        preset = get_preset(config.preset)
        if preset is None:
            raise HTTPException(status_code=400, detail=f"Unknown preset: {config.preset}")

        result = {
            "preset": config.preset,
            "council_models": preset.council_models,
            "chairman_model": preset.chairman_model,
            "research_model": preset.research_model
        }

    # Explicit model overrides take precedence over preset
    if config.council_models:
        # Validate council size
        council_count = len(config.council_models)
        if council_count < MIN_COUNCIL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Council requires at least {MIN_COUNCIL_SIZE} models, got {council_count}"
            )
        if council_count > MAX_COUNCIL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Council allows at most {MAX_COUNCIL_SIZE} models, got {council_count}"
            )

        # Validate each model ID
        for model_id in config.council_models:
            validate_model_id(model_id)
        result["council_models"] = config.council_models

    if config.chairman_model:
        validate_model_id(config.chairman_model)
        result["chairman_model"] = config.chairman_model

    if config.research_model:
        validate_model_id(config.research_model)
        result["research_model"] = config.research_model

    # Add webhook URL override if specified
    if config.webhook_url:
        result["webhook_url"] = config.webhook_url

    return result if result else None


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new conversation.

    Optionally accepts model configuration:
    - preset: Use a predefined model configuration (fast, balanced, comprehensive)
    - council_models: List of provider:model strings for council members
    - chairman_model: provider:model string for the chairman
    - research_model: provider:model string for research (optional)

    Explicit model overrides take precedence over preset values.
    """
    conversation_id = str(uuid.uuid4())

    # Resolve and validate model config
    model_config = resolve_model_config(request.model_config_data)

    conversation = storage.create_conversation(conversation_id, model_config=model_config)

    # Emit webhook for conversation creation
    webhook_url = model_config.get("webhook_url") if model_config else None
    emit_webhook(
        WebhookEvent.CONVERSATION_CREATED,
        conversation_id,
        data={
            "title": conversation["title"],
            "model_config": model_config
        },
        webhook_url=webhook_url
    )

    # Map storage field to response field
    response_data = {
        "id": conversation["id"],
        "created_at": conversation["created_at"],
        "title": conversation["title"],
        "messages": conversation["messages"],
        "model_config_data": conversation.get("model_config")
    }
    return response_data


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    try:
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Map storage field to response field
        return {
            "id": conversation["id"],
            "created_at": conversation["created_at"],
            "title": conversation["title"],
            "messages": conversation["messages"],
            "model_config_data": conversation.get("model_config")
        }
    except InvalidConversationIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PathTraversalError as e:
        raise HTTPException(status_code=400, detail="Invalid conversation path")


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.

    Conversation history is automatically included based on CONVERSATION_CONTEXT_STRATEGY:
    - "chairman_only": Include user messages and chairman's final responses (default)
    - "full": Include all stage 1 responses summarized
    - "none": No history, each query is independent

    Model configuration is loaded from the conversation if set during creation.
    """
    try:
        # Check if conversation exists
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except InvalidConversationIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PathTraversalError as e:
        raise HTTPException(status_code=400, detail="Invalid conversation path")

    # Get model config from conversation (if set)
    model_config = conversation.get("model_config")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Build conversation history for context (before adding new message)
    conversation_history = storage.build_conversation_history(
        conversation_id,
        strategy=CONVERSATION_CONTEXT_STRATEGY,
        max_exchanges=MAX_CONTEXT_EXCHANGES
    )

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content, model_config)
        storage.update_conversation_title(conversation_id, title)

    # Get webhook URL override from conversation config
    webhook_url = model_config.get("webhook_url") if model_config else None

    try:
        # Run the 3-stage council process with conversation history and model config
        stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
            request.content,
            conversation_history=conversation_history,
            model_config=model_config
        )

        # Add assistant message with all stages
        storage.add_assistant_message(
            conversation_id,
            stage1_results,
            stage2_results,
            stage3_result
        )

        # Emit webhook for council completion
        emit_webhook(
            WebhookEvent.COUNCIL_COMPLETE,
            conversation_id,
            data={
                "stage1_model_count": len(stage1_results),
                "stage2_ranking_count": len(stage2_results),
                "chairman_model": stage3_result.get("model"),
                "aggregate_rankings": metadata.get("aggregate_rankings", [])
            },
            webhook_url=webhook_url
        )

        # Return the complete response with metadata
        return {
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "metadata": metadata
        }

    except Exception as e:
        # Emit webhook for council error
        emit_webhook(
            WebhookEvent.COUNCIL_ERROR,
            conversation_id,
            data={"error": str(e)},
            webhook_url=webhook_url
        )
        raise


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.

    Conversation history is automatically included based on CONVERSATION_CONTEXT_STRATEGY:
    - "chairman_only": Include user messages and chairman's final responses (default)
    - "full": Include all stage 1 responses summarized
    - "none": No history, each query is independent

    Model configuration is loaded from the conversation if set during creation.
    """
    try:
        # Check if conversation exists
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except InvalidConversationIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PathTraversalError as e:
        raise HTTPException(status_code=400, detail="Invalid conversation path")

    # Get model config from conversation (if set)
    model_config = conversation.get("model_config")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Build conversation history for context (before adding new message)
    conversation_history = storage.build_conversation_history(
        conversation_id,
        strategy=CONVERSATION_CONTEXT_STRATEGY,
        max_exchanges=MAX_CONTEXT_EXCHANGES
    )

    # Get webhook URL override from conversation config
    webhook_url = model_config.get("webhook_url") if model_config else None

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content, model_config))

            # Stage 1: Collect responses (with conversation history and model config)
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content, conversation_history, model_config)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Emit webhook for stage 1 completion
            emit_webhook(
                WebhookEvent.STAGE1_COMPLETE,
                conversation_id,
                data={
                    "model_count": len(stage1_results),
                    "models": [r.get("model") for r in stage1_results]
                },
                webhook_url=webhook_url
            )

            # Stage 2: Collect rankings (no history needed - rankings are about current responses)
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results, model_config)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Emit webhook for stage 2 completion
            emit_webhook(
                WebhookEvent.STAGE2_COMPLETE,
                conversation_id,
                data={
                    "ranking_count": len(stage2_results),
                    "aggregate_rankings": aggregate_rankings
                },
                webhook_url=webhook_url
            )

            # Stage 3: Synthesize final answer (with conversation history and model config)
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results, conversation_history, model_config)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Emit webhook for stage 3 completion
            emit_webhook(
                WebhookEvent.STAGE3_COMPLETE,
                conversation_id,
                data={"chairman_model": stage3_result.get("model")},
                webhook_url=webhook_url
            )

            # Wait for title generation if it was started (non-critical, don't fail if it errors)
            if title_task:
                try:
                    title = await title_task
                    storage.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
                except Exception as title_error:
                    # Log but don't fail - title generation is non-critical
                    logger = get_logger()
                    logger.warn("Title generation failed", error=str(title_error), conversation_id=conversation_id)

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Emit webhook for council completion
            emit_webhook(
                WebhookEvent.COUNCIL_COMPLETE,
                conversation_id,
                data={
                    "stage1_model_count": len(stage1_results),
                    "stage2_ranking_count": len(stage2_results),
                    "chairman_model": stage3_result.get("model"),
                    "aggregate_rankings": aggregate_rankings
                },
                webhook_url=webhook_url
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Emit webhook for council error
            emit_webhook(
                WebhookEvent.COUNCIL_ERROR,
                conversation_id,
                data={"error": str(e)},
                webhook_url=webhook_url
            )
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
