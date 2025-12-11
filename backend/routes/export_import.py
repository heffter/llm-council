"""Export and import API endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

from ..export_import import (
    export_conversation_json,
    export_conversation_markdown,
    export_conversations_zip,
    validate_import_json,
    validate_import_zip,
    import_conversation_json,
    import_conversations_zip,
    get_export_filename,
    MAX_IMPORT_SIZE_BYTES,
    EXPORT_VERSION,
)
from ..storage_utils import InvalidConversationIdError
from ..logger import get_logger


router = APIRouter(prefix="/api/conversations", tags=["export-import"])


# =============================================================================
# Response Models
# =============================================================================

class ImportResult(BaseModel):
    """Result of an import operation."""
    success: bool
    conversation_ids: List[str]
    warnings: List[str]
    errors: List[str]


class ValidationResponse(BaseModel):
    """Response from validation endpoint."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ExportInfoResponse(BaseModel):
    """Export capability information."""
    supported_formats: List[str]
    export_version: str
    max_import_size_bytes: int


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/export/info", response_model=ExportInfoResponse)
async def get_export_info():
    """
    Get information about export/import capabilities.

    Returns supported formats, version, and limits.
    """
    return ExportInfoResponse(
        supported_formats=["json", "markdown", "zip"],
        export_version=EXPORT_VERSION,
        max_import_size_bytes=MAX_IMPORT_SIZE_BYTES
    )


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = Query("json", regex="^(json|markdown|md)$")
):
    """
    Export a single conversation.

    Args:
        conversation_id: UUID of the conversation to export
        format: Export format - "json" or "markdown" (alias: "md")

    Returns:
        JSON data or Markdown text with appropriate content type
    """
    logger = get_logger()

    try:
        if format == "json":
            data = export_conversation_json(conversation_id)
            filename = get_export_filename(conversation_id, "json")

            return Response(
                content=json.dumps(data, indent=2, ensure_ascii=False),
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        elif format in ("markdown", "md"):
            content = export_conversation_markdown(conversation_id)
            filename = get_export_filename(conversation_id, "md")

            return Response(
                content=content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

    except InvalidConversationIdError as e:
        logger.warn("Export failed - invalid ID", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.warn("Export failed - not found", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Export failed", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.get("/export/collection")
async def export_collection(
    ids: Optional[str] = Query(None, description="Comma-separated conversation IDs, or omit for all"),
    include_markdown: bool = Query(True, description="Include Markdown versions in ZIP")
):
    """
    Export multiple conversations as a ZIP archive.

    Args:
        ids: Comma-separated list of conversation IDs, or None for all conversations
        include_markdown: Whether to include Markdown versions (default: True)

    Returns:
        ZIP archive containing JSON exports and optionally Markdown
    """
    logger = get_logger()

    try:
        # Parse conversation IDs
        conversation_ids = None
        if ids:
            conversation_ids = [id.strip() for id in ids.split(",") if id.strip()]

        zip_data = export_conversations_zip(
            conversation_ids=conversation_ids,
            include_markdown=include_markdown
        )

        filename = get_export_filename("collection", "zip")

        logger.info(
            "Collection exported",
            conversation_count=len(conversation_ids) if conversation_ids else "all",
            include_markdown=include_markdown
        )

        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error("Collection export failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


# =============================================================================
# Import Endpoints
# =============================================================================

@router.post("/import", response_model=ImportResult)
async def import_conversations(
    file: UploadFile = File(...),
    preserve_ids: bool = Query(False, description="Try to preserve original conversation IDs")
):
    """
    Import conversations from a JSON or ZIP file.

    Accepts:
    - Single conversation JSON
    - Wrapped conversation JSON (with metadata)
    - ZIP archive with multiple conversations

    Args:
        file: Uploaded file (JSON or ZIP)
        preserve_ids: Whether to preserve original IDs if valid and available

    Returns:
        ImportResult with success status, imported IDs, and any warnings/errors
    """
    logger = get_logger()

    # Check file size
    contents = await file.read()
    if len(contents) > MAX_IMPORT_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_IMPORT_SIZE_BYTES} bytes"
        )

    filename = file.filename or ""
    content_type = file.content_type or ""

    logger.info(
        "Import started",
        filename=filename,
        content_type=content_type,
        size_bytes=len(contents)
    )

    try:
        # Determine file type
        is_zip = (
            filename.lower().endswith('.zip') or
            content_type == "application/zip" or
            contents[:4] == b'PK\x03\x04'  # ZIP magic bytes
        )

        if is_zip:
            # Import ZIP archive
            validation = validate_import_zip(contents)
            if not validation.valid:
                return ImportResult(
                    success=False,
                    conversation_ids=[],
                    warnings=validation.warnings,
                    errors=validation.errors
                )

            imported_ids, warnings = import_conversations_zip(
                contents,
                preserve_ids=preserve_ids
            )

            return ImportResult(
                success=True,
                conversation_ids=imported_ids,
                warnings=warnings,
                errors=[]
            )

        else:
            # Import JSON
            try:
                data = json.loads(contents.decode('utf-8'))
            except json.JSONDecodeError as e:
                return ImportResult(
                    success=False,
                    conversation_ids=[],
                    warnings=[],
                    errors=[f"Invalid JSON: {e}"]
                )

            validation = validate_import_json(data)
            if not validation.valid:
                return ImportResult(
                    success=False,
                    conversation_ids=[],
                    warnings=validation.warnings,
                    errors=validation.errors
                )

            new_id, warnings = import_conversation_json(
                validation.data,
                preserve_id=preserve_ids
            )

            return ImportResult(
                success=True,
                conversation_ids=[new_id],
                warnings=warnings,
                errors=[]
            )

    except Exception as e:
        logger.error("Import failed", error=str(e))
        return ImportResult(
            success=False,
            conversation_ids=[],
            warnings=[],
            errors=[f"Import failed: {e}"]
        )


@router.post("/import/validate", response_model=ValidationResponse)
async def validate_import(
    file: UploadFile = File(...)
):
    """
    Validate a file for import without actually importing it.

    Useful for checking file validity before committing to import.

    Args:
        file: Uploaded file (JSON or ZIP)

    Returns:
        ValidationResponse with validity status, errors, and warnings
    """
    # Check file size
    contents = await file.read()
    if len(contents) > MAX_IMPORT_SIZE_BYTES:
        return ValidationResponse(
            valid=False,
            errors=[f"File too large. Maximum size is {MAX_IMPORT_SIZE_BYTES} bytes"],
            warnings=[]
        )

    filename = file.filename or ""
    content_type = file.content_type or ""

    try:
        # Determine file type
        is_zip = (
            filename.lower().endswith('.zip') or
            content_type == "application/zip" or
            contents[:4] == b'PK\x03\x04'
        )

        if is_zip:
            validation = validate_import_zip(contents)
        else:
            try:
                data = json.loads(contents.decode('utf-8'))
                validation = validate_import_json(data)
            except json.JSONDecodeError as e:
                return ValidationResponse(
                    valid=False,
                    errors=[f"Invalid JSON: {e}"],
                    warnings=[]
                )

        return ValidationResponse(
            valid=validation.valid,
            errors=validation.errors,
            warnings=validation.warnings
        )

    except Exception as e:
        return ValidationResponse(
            valid=False,
            errors=[f"Validation failed: {e}"],
            warnings=[]
        )
