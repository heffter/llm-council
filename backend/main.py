"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .config import validate_config, COUNCIL_MODELS, CHAIRMAN_MODEL, RESEARCH_MODEL
from .storage_utils import InvalidConversationIdError, PathTraversalError
from .middleware import shared_secret_middleware, rate_limit_middleware
from .providers import get_registry
from .logger import get_logger

logger = get_logger()

app = FastAPI(title="LLM Council API")


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
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(shared_secret_middleware)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/health")
async def health():
    """
    Health and configuration endpoint.

    Returns system status and enabled provider information (no secrets).
    Can be disabled by setting EXPOSE_HEALTH_ENDPOINT=false.
    """
    import os

    # Check if endpoint is enabled
    if os.getenv("EXPOSE_HEALTH_ENDPOINT", "true").lower() != "true":
        raise HTTPException(status_code=404, detail="Endpoint not found")

    registry = get_registry()

    # Build provider status
    providers = {}
    for provider_id in ['openai', 'anthropic', 'gemini', 'perplexity', 'openrouter']:
        providers[provider_id] = {
            "enabled": registry.is_provider_configured(provider_id)
        }

    # Build role configuration (without secrets)
    roles = {
        "council": COUNCIL_MODELS,
        "chairman": CHAIRMAN_MODEL,
        "research": RESEARCH_MODEL if RESEARCH_MODEL else None
    }

    # Storage configuration info
    from .config import DATA_DIR
    storage_config = {
        "path": DATA_DIR,
        "encrypted": False,
        "description": "Conversations are stored as unencrypted JSON files on local disk."
    }

    return {
        "status": "ok",
        "providers": providers,
        "roles": roles,
        "storage": storage_config
    }


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    try:
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except InvalidConversationIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PathTraversalError as e:
        raise HTTPException(status_code=400, detail="Invalid conversation path")


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
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

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
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

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            try:
                stage1_results = await stage1_collect_responses(request.content)
                yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"
            except Exception as e:
                logger.error("Stage 1 failed", error=str(e), conversation_id=conversation_id)
                yield f"data: {json.dumps({{'type': 'error', 'stage': 'stage1', 'message': str(e), 'retryable': True}})}\n\n"
                return

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            try:
                stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
                aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
                yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"
            except Exception as e:
                logger.error("Stage 2 failed", error=str(e), conversation_id=conversation_id)
                yield f"data: {json.dumps({{'type': 'error', 'stage': 'stage2', 'message': str(e), 'retryable': True}})}\n\n"
                return

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            try:
                stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"
            except Exception as e:
                logger.error("Stage 3 failed", error=str(e), conversation_id=conversation_id)
                yield f"data: {json.dumps({{'type': 'error', 'stage': 'stage3', 'message': str(e), 'retryable': True}})}\n\n"
                return

            # Wait for title generation if it was started (non-critical, catch errors)
            if title_task:
                try:
                    title = await title_task
                    storage.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
                except Exception as e:
                    logger.warn("Title generation failed (non-critical)", error=str(e), conversation_id=conversation_id)
                    # Don't send error event for title failures - it's non-critical

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error("Unexpected error in SSE stream", error=str(e), conversation_id=conversation_id)
            yield f"data: {json.dumps({{'type': 'error', 'message': str(e), 'retryable': False}})}\n\n"

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
