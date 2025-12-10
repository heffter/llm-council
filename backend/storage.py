"""JSON-based storage for conversations."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR
from .storage_utils import (
    validate_conversation_id,
    get_safe_conversation_path,
    truncate_for_storage,
    InvalidConversationIdError,
    PathTraversalError
)


# Maximum response size for storage (256KB default)
MAX_STORED_RESPONSE_BYTES = int(os.getenv("MAX_STORED_RESPONSE_BYTES", "262144"))


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """
    Get the safe file path for a conversation.

    Args:
        conversation_id: Conversation UUID

    Returns:
        Absolute path to conversation file

    Raises:
        InvalidConversationIdError: If conversation_id is not valid UUID v4
        PathTraversalError: If path traversal is attempted
    """
    return get_safe_conversation_path(conversation_id, DATA_DIR)


def create_conversation(
    conversation_id: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: UUID v4 identifier for the conversation
        model_config: Optional model configuration override with keys:
            - preset: Name of preset to use (fast, balanced, comprehensive)
            - council_models: List of provider:model strings for council
            - chairman_model: provider:model string for chairman
            - research_model: provider:model string for research (optional)

    Returns:
        New conversation dict

    Raises:
        InvalidConversationIdError: If conversation_id is not valid UUID v4
    """
    # Validate UUID before proceeding
    validate_conversation_id(conversation_id)
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": []
    }

    # Store model config if provided
    if model_config:
        conversation["model_config"] = model_config

    # Save to file
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: UUID v4 identifier for the conversation

    Returns:
        Conversation dict or None if not found

    Raises:
        InvalidConversationIdError: If conversation_id is not valid UUID v4
    """
    # Validate UUID before proceeding
    validate_conversation_id(conversation_id)

    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r') as f:
            data = json.load(f)
            # Validate loaded data structure
            if not isinstance(data, dict) or 'id' not in data or 'messages' not in data:
                raise ValueError("Corrupted conversation file")
            return data
    except (json.JSONDecodeError, ValueError) as e:
        # Log error but don't crash - return None for corrupted files
        print(f"Error loading conversation {conversation_id}: {e}")
        return None


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                # Return metadata only
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "message_count": len(data["messages"])
                })

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.
    Truncates oversized responses before storage.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Truncate responses for storage
    truncated_stage1 = []
    for result in stage1:
        truncated_result = result.copy()
        if 'response' in truncated_result:
            truncated_result['response'] = truncate_for_storage(
                truncated_result['response'],
                MAX_STORED_RESPONSE_BYTES
            )
        truncated_stage1.append(truncated_result)

    truncated_stage2 = []
    for result in stage2:
        truncated_result = result.copy()
        if 'ranking' in truncated_result:
            truncated_result['ranking'] = truncate_for_storage(
                truncated_result['ranking'],
                MAX_STORED_RESPONSE_BYTES
            )
        truncated_stage2.append(truncated_result)

    truncated_stage3 = stage3.copy()
    if 'response' in truncated_stage3:
        truncated_stage3['response'] = truncate_for_storage(
            truncated_stage3['response'],
            MAX_STORED_RESPONSE_BYTES
        )

    conversation["messages"].append({
        "role": "assistant",
        "stage1": truncated_stage1,
        "stage2": truncated_stage2,
        "stage3": truncated_stage3
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)


def build_conversation_history(
    conversation_id: str,
    strategy: str = "chairman_only",
    max_exchanges: int = 5
) -> List[Dict[str, str]]:
    """
    Build a list of messages representing conversation history for LLM context.

    The history is formatted as alternating user/assistant messages that can be
    prepended to new queries to provide conversation context.

    Args:
        conversation_id: Conversation identifier
        strategy: How to extract assistant responses:
            - "chairman_only": Use only stage3 (chairman) response (cost-efficient)
            - "full": Include all stage1 responses summarized (comprehensive)
            - "none": Return empty list (no history)
        max_exchanges: Maximum number of user-assistant exchanges to include

    Returns:
        List of message dicts with 'role' and 'content' keys, ordered chronologically.
        Returns empty list if conversation not found or strategy is "none".
    """
    if strategy == "none":
        return []

    conversation = get_conversation(conversation_id)
    if conversation is None:
        return []

    messages = conversation.get("messages", [])
    if not messages:
        return []

    # Build pairs of (user_message, assistant_message)
    history = []
    i = 0
    while i < len(messages):
        msg = messages[i]

        if msg.get("role") == "user":
            user_content = msg.get("content", "")

            # Look for the next assistant message
            if i + 1 < len(messages) and messages[i + 1].get("role") == "assistant":
                assistant_msg = messages[i + 1]

                if strategy == "chairman_only":
                    # Extract only the chairman's final response (stage3)
                    stage3 = assistant_msg.get("stage3", {})
                    assistant_content = stage3.get("response", "")
                elif strategy == "full":
                    # Build a summary including all stage1 responses
                    stage1 = assistant_msg.get("stage1", [])
                    stage3 = assistant_msg.get("stage3", {})

                    # Summarize stage1 responses
                    stage1_summary = "\n\n".join([
                        f"**{r.get('model', 'Unknown')}**: {r.get('response', '')[:500]}..."
                        if len(r.get('response', '')) > 500
                        else f"**{r.get('model', 'Unknown')}**: {r.get('response', '')}"
                        for r in stage1
                    ])

                    chairman_response = stage3.get("response", "")

                    assistant_content = f"Council Responses:\n{stage1_summary}\n\nFinal Answer:\n{chairman_response}"
                else:
                    assistant_content = ""

                if user_content and assistant_content:
                    history.append({"role": "user", "content": user_content})
                    history.append({"role": "assistant", "content": assistant_content})

                i += 2  # Skip both user and assistant messages
            else:
                i += 1  # No assistant response yet, skip just the user message
        else:
            i += 1  # Skip orphaned assistant messages

    # Limit to max_exchanges (each exchange = 2 messages)
    max_messages = max_exchanges * 2
    if len(history) > max_messages:
        # Keep only the most recent exchanges
        history = history[-max_messages:]

    return history
