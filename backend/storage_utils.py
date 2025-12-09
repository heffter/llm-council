"""Storage utilities for conversation safety and validation."""

import os
from pathlib import Path
from uuid import UUID
from typing import Optional


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class InvalidConversationIdError(StorageError):
    """Raised when conversation ID is not a valid UUID v4."""
    pass


class PathTraversalError(StorageError):
    """Raised when path traversal is attempted."""
    pass


def validate_conversation_id(conversation_id: str) -> None:
    """
    Validate that conversation ID is a valid UUID v4.

    Args:
        conversation_id: String to validate

    Raises:
        InvalidConversationIdError: If not a valid UUID v4
    """
    try:
        uuid_obj = UUID(conversation_id)
        # Verify it's actually UUID v4 (not v1, v3, or v5)
        if uuid_obj.version != 4:
            raise InvalidConversationIdError(
                f"conversation_id must be a valid UUID v4, got version {uuid_obj.version}: {conversation_id}"
            )
        # Ensure string matches canonical UUID format
        if str(uuid_obj) != conversation_id:
            raise InvalidConversationIdError(
                f"conversation_id must be a valid UUID v4 in canonical format"
            )
    except (ValueError, AttributeError) as e:
        raise InvalidConversationIdError(
            f"conversation_id must be a valid UUID v4: {conversation_id}"
        )


def get_safe_conversation_path(conversation_id: str, base_dir: str) -> str:
    """
    Get safe file path for a conversation, preventing path traversal.

    Args:
        conversation_id: Validated conversation ID
        base_dir: Base directory for conversations

    Returns:
        Absolute path to conversation file

    Raises:
        InvalidConversationIdError: If conversation_id is not valid UUID v4
        PathTraversalError: If resulting path is outside base_dir
    """
    # Validate UUID first
    validate_conversation_id(conversation_id)

    # Resolve base directory to absolute path
    base_path = Path(base_dir).resolve()

    # Construct safe filename (UUID + .json)
    safe_filename = f"{conversation_id}.json"

    # Resolve full path
    full_path = (base_path / safe_filename).resolve()

    # Ensure path is within base directory
    try:
        full_path.relative_to(base_path)
    except ValueError:
        raise PathTraversalError(
            f"Invalid conversation path: attempted path traversal"
        )

    return str(full_path)


def truncate_for_storage(text: str, max_bytes: int = 262144) -> str:
    """
    Truncate text to maximum byte size for storage.

    Uses UTF-8 encoding and adds [TRUNCATED] marker if text exceeds limit.

    Args:
        text: Text to truncate
        max_bytes: Maximum size in bytes (default: 256KB)

    Returns:
        Original text if under limit, truncated text with marker otherwise
    """
    if not text:
        return text

    encoded = text.encode('utf-8')

    if len(encoded) <= max_bytes:
        return text

    # Truncate to max_bytes and decode, handling potential incomplete UTF-8
    truncated_bytes = encoded[:max_bytes]

    # Decode with error handling for incomplete characters
    try:
        truncated_text = truncated_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # If we cut in the middle of a multi-byte character, try removing last few bytes
        for i in range(1, 5):  # UTF-8 chars are max 4 bytes
            try:
                truncated_text = truncated_bytes[:-i].decode('utf-8')
                break
            except UnicodeDecodeError:
                continue
        else:
            # Fallback: use replacement character
            truncated_text = truncated_bytes.decode('utf-8', errors='replace')

    return truncated_text + '\n[TRUNCATED]'
