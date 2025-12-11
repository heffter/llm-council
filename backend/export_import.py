"""Export and import functionality for conversations."""

import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .storage import get_conversation, save_conversation, list_conversations, DATA_DIR
from .storage_utils import validate_conversation_id, InvalidConversationIdError
from .logger import get_logger

# Export format version for compatibility checking
EXPORT_VERSION = "1.0"

# Maximum file size for imports (10MB)
MAX_IMPORT_SIZE_BYTES = 10 * 1024 * 1024


@dataclass
class ExportMetadata:
    """Metadata included in exports."""
    export_version: str = EXPORT_VERSION
    exported_at: str = ""
    source_application: str = "llm-council"

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "export_version": self.export_version,
            "exported_at": self.exported_at,
            "source_application": self.source_application
        }


@dataclass
class ValidationResult:
    """Result of import validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None


# =============================================================================
# JSON Export/Import
# =============================================================================

def export_conversation_json(conversation_id: str) -> Dict[str, Any]:
    """
    Export a conversation as JSON with metadata.

    Args:
        conversation_id: UUID of the conversation to export

    Returns:
        Dict containing conversation data and export metadata

    Raises:
        InvalidConversationIdError: If conversation_id is invalid
        ValueError: If conversation not found
    """
    validate_conversation_id(conversation_id)
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    metadata = ExportMetadata()

    return {
        "metadata": metadata.to_dict(),
        "conversation": conversation
    }


def validate_import_json(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate imported JSON data.

    Args:
        data: The parsed JSON data to validate

    Returns:
        ValidationResult with valid flag, errors, and warnings
    """
    errors = []
    warnings = []

    # Check for required top-level structure
    if "conversation" not in data:
        # Support both wrapped format and raw conversation format
        if "id" in data and "messages" in data:
            # Raw conversation format - wrap it
            data = {"conversation": data}
        else:
            errors.append("Missing 'conversation' field or valid conversation structure")
            return ValidationResult(valid=False, errors=errors)

    conversation = data.get("conversation", {})

    # Validate required fields
    required_fields = ["id", "messages"]
    for field_name in required_fields:
        if field_name not in conversation:
            errors.append(f"Missing required field: {field_name}")

    if errors:
        return ValidationResult(valid=False, errors=errors)

    # Validate conversation ID format
    conv_id = conversation.get("id", "")
    try:
        # Check if it's a valid UUID
        uuid.UUID(conv_id, version=4)
    except (ValueError, AttributeError):
        warnings.append(f"Invalid or missing UUID, will generate new ID")

    # Validate messages structure
    messages = conversation.get("messages", [])
    if not isinstance(messages, list):
        errors.append("'messages' must be a list")
        return ValidationResult(valid=False, errors=errors)

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            errors.append(f"Message {i} must be a dict")
            continue

        role = msg.get("role")
        if role not in ("user", "assistant"):
            errors.append(f"Message {i} has invalid role: {role}")

        if role == "user" and "content" not in msg:
            errors.append(f"User message {i} missing 'content'")

        if role == "assistant":
            # Assistant messages should have stage data
            if not any(k in msg for k in ("stage1", "stage2", "stage3", "content")):
                warnings.append(f"Assistant message {i} missing stage data")

    # Check metadata if present
    metadata = data.get("metadata", {})
    if metadata:
        export_version = metadata.get("export_version", "")
        if export_version and export_version != EXPORT_VERSION:
            warnings.append(f"Export version mismatch: {export_version} vs {EXPORT_VERSION}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=data
    )


def import_conversation_json(
    data: Dict[str, Any],
    preserve_id: bool = False
) -> Tuple[str, List[str]]:
    """
    Import a conversation from JSON data.

    Args:
        data: Validated JSON data (should pass validate_import_json first)
        preserve_id: If True, try to preserve the original ID if valid and available

    Returns:
        Tuple of (new_conversation_id, list_of_warnings)

    Raises:
        ValueError: If data is invalid or import fails
    """
    logger = get_logger()
    warnings = []

    # Extract conversation data
    if "conversation" in data:
        conversation = data["conversation"].copy()
    else:
        conversation = data.copy()

    original_id = conversation.get("id", "")

    # Determine the new conversation ID
    new_id = None
    if preserve_id and original_id:
        try:
            validate_conversation_id(original_id)
            # Check if ID already exists
            existing = get_conversation(original_id)
            if existing is None:
                new_id = original_id
            else:
                warnings.append(f"ID {original_id} already exists, generating new ID")
        except InvalidConversationIdError:
            warnings.append(f"Invalid original ID format, generating new ID")

    if new_id is None:
        new_id = str(uuid.uuid4())

    # Update conversation with new ID
    conversation["id"] = new_id

    # Ensure required fields have defaults
    if "created_at" not in conversation:
        conversation["created_at"] = datetime.utcnow().isoformat()

    if "title" not in conversation:
        conversation["title"] = "Imported Conversation"

    if "messages" not in conversation:
        conversation["messages"] = []

    # Save the conversation
    save_conversation(conversation)

    logger.info(
        "Conversation imported",
        original_id=original_id,
        new_id=new_id,
        message_count=len(conversation.get("messages", []))
    )

    return new_id, warnings


# =============================================================================
# Markdown Export
# =============================================================================

def export_conversation_markdown(conversation_id: str) -> str:
    """
    Export a conversation as formatted Markdown.

    Args:
        conversation_id: UUID of the conversation to export

    Returns:
        Markdown-formatted string

    Raises:
        InvalidConversationIdError: If conversation_id is invalid
        ValueError: If conversation not found
    """
    validate_conversation_id(conversation_id)
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    lines = []

    # Header
    title = conversation.get("title", "Untitled Conversation")
    lines.append(f"# {title}")
    lines.append("")

    # Metadata section
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **ID:** `{conversation['id']}`")
    lines.append(f"- **Created:** {conversation.get('created_at', 'Unknown')}")
    lines.append(f"- **Exported:** {datetime.now(timezone.utc).isoformat()}")

    # Model config if present
    model_config = conversation.get("model_config")
    if model_config:
        lines.append("")
        lines.append("### Council Configuration")
        lines.append("")

        if "preset" in model_config:
            lines.append(f"- **Preset:** {model_config['preset']}")

        council_models = model_config.get("council_models", [])
        if council_models:
            lines.append(f"- **Council Models:**")
            for model in council_models:
                lines.append(f"  - `{model}`")

        if "chairman_model" in model_config:
            lines.append(f"- **Chairman:** `{model_config['chairman_model']}`")

        if model_config.get("research_model"):
            lines.append(f"- **Research:** `{model_config['research_model']}`")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Messages
    lines.append("## Conversation")
    lines.append("")

    messages = conversation.get("messages", [])
    exchange_num = 0

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")

        if role == "user":
            exchange_num += 1
            lines.append(f"### Exchange {exchange_num}")
            lines.append("")
            lines.append("#### User Query")
            lines.append("")
            lines.append(msg.get("content", ""))
            lines.append("")

        elif role == "assistant":
            # Stage 1: Individual Responses
            stage1 = msg.get("stage1", [])
            if stage1:
                lines.append("#### Stage 1: Individual Responses")
                lines.append("")

                for response in stage1:
                    model = response.get("model", "Unknown Model")
                    content = response.get("response", "")
                    lines.append(f"##### {model}")
                    lines.append("")
                    lines.append(content)
                    lines.append("")

            # Stage 2: Rankings
            stage2 = msg.get("stage2", [])
            if stage2:
                lines.append("#### Stage 2: Peer Rankings")
                lines.append("")

                for ranking in stage2:
                    model = ranking.get("model", "Unknown Model")
                    parsed = ranking.get("parsed_ranking", [])
                    lines.append(f"##### {model}'s Ranking")
                    lines.append("")

                    if parsed:
                        lines.append("| Rank | Response |")
                        lines.append("|------|----------|")
                        for rank, label in enumerate(parsed, 1):
                            lines.append(f"| {rank} | {label} |")
                        lines.append("")

                    # Include full ranking text in collapsed section
                    full_ranking = ranking.get("ranking", "")
                    if full_ranking:
                        lines.append("<details>")
                        lines.append("<summary>Full Ranking Analysis</summary>")
                        lines.append("")
                        lines.append(full_ranking)
                        lines.append("")
                        lines.append("</details>")
                        lines.append("")

            # Stage 3: Final Answer
            stage3 = msg.get("stage3", {})
            if stage3:
                lines.append("#### Stage 3: Final Answer")
                lines.append("")
                chairman = stage3.get("model", "Unknown")
                lines.append(f"*Chairman: {chairman}*")
                lines.append("")
                lines.append(stage3.get("response", ""))
                lines.append("")

            lines.append("---")
            lines.append("")

    # Footer
    lines.append("")
    lines.append(f"*Exported from LLM Council on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*")

    return "\n".join(lines)


# =============================================================================
# ZIP Collection Export/Import
# =============================================================================

@dataclass
class ZipManifest:
    """Manifest for ZIP collection exports."""
    export_version: str = EXPORT_VERSION
    exported_at: str = ""
    source_application: str = "llm-council"
    conversation_count: int = 0
    conversations: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "export_version": self.export_version,
            "exported_at": self.exported_at,
            "source_application": self.source_application,
            "conversation_count": self.conversation_count,
            "conversations": self.conversations
        }


def export_conversations_zip(
    conversation_ids: Optional[List[str]] = None,
    include_markdown: bool = True
) -> bytes:
    """
    Export multiple conversations as a ZIP archive.

    Args:
        conversation_ids: List of conversation IDs to export, or None for all
        include_markdown: Whether to include Markdown versions

    Returns:
        ZIP file as bytes
    """
    logger = get_logger()

    # If no IDs specified, export all conversations
    if conversation_ids is None:
        all_convs = list_conversations()
        conversation_ids = [c["id"] for c in all_convs]

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    manifest = ZipManifest(conversation_count=len(conversation_ids))

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for conv_id in conversation_ids:
            try:
                # Export JSON
                export_data = export_conversation_json(conv_id)
                json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
                json_filename = f"conversations/{conv_id}.json"
                zf.writestr(json_filename, json_content)

                # Export Markdown if requested
                md_filename = None
                if include_markdown:
                    md_content = export_conversation_markdown(conv_id)
                    md_filename = f"markdown/{conv_id}.md"
                    zf.writestr(md_filename, md_content)

                # Add to manifest
                conv = export_data.get("conversation", {})
                manifest.conversations.append({
                    "id": conv_id,
                    "title": conv.get("title", "Untitled"),
                    "created_at": conv.get("created_at", ""),
                    "message_count": len(conv.get("messages", [])),
                    "json_file": json_filename,
                    "markdown_file": md_filename
                })

            except Exception as e:
                logger.warn(
                    "Failed to export conversation",
                    conversation_id=conv_id,
                    error=str(e)
                )

        # Write manifest
        manifest_content = json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False)
        zf.writestr("manifest.json", manifest_content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def validate_import_zip(zip_data: bytes) -> ValidationResult:
    """
    Validate a ZIP archive for import.

    Args:
        zip_data: ZIP file as bytes

    Returns:
        ValidationResult with valid flag, errors, warnings, and parsed data
    """
    errors = []
    warnings = []
    conversations = []

    try:
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            # Check for manifest
            if "manifest.json" not in zf.namelist():
                warnings.append("No manifest.json found, scanning for conversation files")

            # Find and validate conversation files
            json_files = [f for f in zf.namelist() if f.endswith('.json') and f != 'manifest.json']

            if not json_files:
                errors.append("No conversation JSON files found in archive")
                return ValidationResult(valid=False, errors=errors)

            for json_file in json_files:
                try:
                    content = zf.read(json_file).decode('utf-8')
                    data = json.loads(content)

                    # Validate each conversation
                    result = validate_import_json(data)
                    if result.valid:
                        conversations.append({
                            "filename": json_file,
                            "data": result.data
                        })
                    else:
                        errors.extend([f"{json_file}: {e}" for e in result.errors])

                    warnings.extend([f"{json_file}: {w}" for w in result.warnings])

                except json.JSONDecodeError as e:
                    errors.append(f"{json_file}: Invalid JSON - {e}")
                except Exception as e:
                    errors.append(f"{json_file}: Error reading - {e}")

    except zipfile.BadZipFile:
        errors.append("Invalid ZIP file")
        return ValidationResult(valid=False, errors=errors)
    except Exception as e:
        errors.append(f"Error processing ZIP: {e}")
        return ValidationResult(valid=False, errors=errors)

    if not conversations:
        errors.append("No valid conversations found in archive")
        return ValidationResult(valid=False, errors=errors)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data={"conversations": conversations}
    )


def import_conversations_zip(
    zip_data: bytes,
    preserve_ids: bool = False
) -> Tuple[List[str], List[str]]:
    """
    Import conversations from a ZIP archive.

    Args:
        zip_data: ZIP file as bytes
        preserve_ids: Whether to try to preserve original IDs

    Returns:
        Tuple of (list of imported conversation IDs, list of warnings)
    """
    logger = get_logger()

    # Validate first
    validation = validate_import_zip(zip_data)
    if not validation.valid:
        raise ValueError(f"Invalid ZIP: {'; '.join(validation.errors)}")

    imported_ids = []
    all_warnings = validation.warnings.copy()

    conversations = validation.data.get("conversations", [])

    for conv_info in conversations:
        try:
            data = conv_info["data"]
            new_id, warnings = import_conversation_json(data, preserve_id=preserve_ids)
            imported_ids.append(new_id)
            all_warnings.extend(warnings)
        except Exception as e:
            all_warnings.append(f"Failed to import {conv_info['filename']}: {e}")

    logger.info(
        "ZIP import completed",
        imported_count=len(imported_ids),
        warning_count=len(all_warnings)
    )

    return imported_ids, all_warnings


# =============================================================================
# Utility Functions
# =============================================================================

def get_export_filename(conversation_id: str, format: str) -> str:
    """
    Generate a filename for export.

    Args:
        conversation_id: UUID of the conversation
        format: Export format (json, md, zip)

    Returns:
        Suggested filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "zip":
        return f"llm-council-export_{timestamp}.zip"

    # Get conversation title for filename
    try:
        conv = get_conversation(conversation_id)
        if conv:
            # Sanitize title for filename
            title = conv.get("title", "conversation")
            title = re.sub(r'[^\w\s-]', '', title)
            title = re.sub(r'[\s]+', '_', title)
            title = title[:50]  # Limit length
            return f"{title}_{conversation_id[:8]}.{format}"
    except Exception:
        pass

    return f"conversation_{conversation_id[:8]}.{format}"
