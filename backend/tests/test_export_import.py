"""Tests for export/import functionality."""

import json
import uuid
import zipfile
import io
import pytest
from unittest.mock import patch, MagicMock

from backend.export_import import (
    ExportMetadata,
    ValidationResult,
    ZipManifest,
    export_conversation_json,
    export_conversation_markdown,
    export_conversations_zip,
    validate_import_json,
    validate_import_zip,
    import_conversation_json,
    import_conversations_zip,
    get_export_filename,
    EXPORT_VERSION,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_conversation():
    """Create a sample conversation for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2024-01-15T10:30:00.000000",
        "title": "Test Conversation",
        "messages": [
            {
                "role": "user",
                "content": "What is the meaning of life?"
            },
            {
                "role": "assistant",
                "stage1": [
                    {"model": "openai:gpt-4", "response": "The meaning of life is 42."},
                    {"model": "anthropic:claude-3", "response": "Life's meaning is subjective."}
                ],
                "stage2": [
                    {
                        "model": "openai:gpt-4",
                        "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                        "parsed_ranking": ["Response B", "Response A"]
                    }
                ],
                "stage3": {
                    "model": "anthropic:claude-3",
                    "response": "The council agrees that the meaning of life is both personal and philosophical."
                }
            }
        ],
        "model_config": {
            "preset": "balanced",
            "council_models": ["openai:gpt-4", "anthropic:claude-3"],
            "chairman_model": "anthropic:claude-3"
        }
    }


@pytest.fixture
def sample_export_data(sample_conversation):
    """Create sample export data."""
    return {
        "metadata": {
            "export_version": EXPORT_VERSION,
            "exported_at": "2024-01-15T12:00:00+00:00",
            "source_application": "llm-council"
        },
        "conversation": sample_conversation
    }


# =============================================================================
# Test ExportMetadata
# =============================================================================

class TestExportMetadata:
    """Tests for ExportMetadata dataclass."""

    def test_default_values(self):
        """Test metadata has correct defaults."""
        meta = ExportMetadata()
        assert meta.export_version == EXPORT_VERSION
        assert meta.source_application == "llm-council"
        assert meta.exported_at  # Should have a timestamp

    def test_to_dict(self):
        """Test metadata serialization."""
        meta = ExportMetadata(exported_at="2024-01-15T12:00:00Z")
        result = meta.to_dict()

        assert result["export_version"] == EXPORT_VERSION
        assert result["exported_at"] == "2024-01-15T12:00:00Z"
        assert result["source_application"] == "llm-council"


# =============================================================================
# Test JSON Export
# =============================================================================

class TestExportConversationJson:
    """Tests for JSON export functionality."""

    def test_export_success(self, sample_conversation):
        """Test successful JSON export."""
        with patch('backend.export_import.get_conversation', return_value=sample_conversation):
            with patch('backend.export_import.validate_conversation_id'):
                result = export_conversation_json(sample_conversation["id"])

        assert "metadata" in result
        assert "conversation" in result
        assert result["conversation"]["id"] == sample_conversation["id"]
        assert result["metadata"]["export_version"] == EXPORT_VERSION

    def test_export_not_found(self):
        """Test export fails for missing conversation."""
        with patch('backend.export_import.get_conversation', return_value=None):
            with patch('backend.export_import.validate_conversation_id'):
                with pytest.raises(ValueError, match="not found"):
                    export_conversation_json("550e8400-e29b-41d4-a716-446655440000")


# =============================================================================
# Test JSON Import Validation
# =============================================================================

class TestValidateImportJson:
    """Tests for JSON import validation."""

    def test_valid_wrapped_format(self, sample_export_data):
        """Test validation of wrapped export format."""
        result = validate_import_json(sample_export_data)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_raw_conversation(self, sample_conversation):
        """Test validation of raw conversation format."""
        result = validate_import_json(sample_conversation)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_conversation_field(self):
        """Test validation fails without conversation data."""
        result = validate_import_json({"metadata": {}})

        assert result.valid is False
        assert any("conversation" in e.lower() for e in result.errors)

    def test_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        result = validate_import_json({"conversation": {}})

        assert result.valid is False
        assert any("id" in e.lower() or "messages" in e.lower() for e in result.errors)

    def test_invalid_messages_type(self):
        """Test validation fails with non-list messages."""
        result = validate_import_json({
            "conversation": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "messages": "not a list"
            }
        })

        assert result.valid is False
        assert any("list" in e.lower() for e in result.errors)

    def test_invalid_message_role(self, sample_conversation):
        """Test validation catches invalid message roles."""
        sample_conversation["messages"][0]["role"] = "invalid"
        result = validate_import_json({"conversation": sample_conversation})

        assert result.valid is False

    def test_warns_on_invalid_uuid(self):
        """Test validation warns about invalid UUID."""
        result = validate_import_json({
            "conversation": {
                "id": "not-a-uuid",
                "messages": []
            }
        })

        assert result.valid is True
        assert any("uuid" in w.lower() for w in result.warnings)

    def test_warns_on_version_mismatch(self):
        """Test validation warns about version mismatch."""
        result = validate_import_json({
            "metadata": {"export_version": "0.1"},
            "conversation": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "messages": []
            }
        })

        assert result.valid is True
        assert any("version" in w.lower() for w in result.warnings)


# =============================================================================
# Test JSON Import
# =============================================================================

class TestImportConversationJson:
    """Tests for JSON import functionality."""

    def test_import_generates_new_id(self, sample_export_data):
        """Test import generates new ID by default."""
        with patch('backend.export_import.save_conversation') as mock_save:
            with patch('backend.export_import.get_conversation', return_value=None):
                new_id, warnings = import_conversation_json(sample_export_data, preserve_id=False)

        # Should generate a new UUID
        assert new_id != sample_export_data["conversation"]["id"]
        assert uuid.UUID(new_id, version=4)  # Valid UUID v4

        # Should have saved the conversation
        mock_save.assert_called_once()
        saved_conv = mock_save.call_args[0][0]
        assert saved_conv["id"] == new_id

    def test_import_preserves_id_when_available(self, sample_export_data):
        """Test import preserves ID when requested and available."""
        original_id = sample_export_data["conversation"]["id"]

        with patch('backend.export_import.save_conversation') as mock_save:
            with patch('backend.export_import.get_conversation', return_value=None):
                with patch('backend.export_import.validate_conversation_id'):
                    new_id, warnings = import_conversation_json(sample_export_data, preserve_id=True)

        assert new_id == original_id

    def test_import_generates_new_id_on_collision(self, sample_export_data, sample_conversation):
        """Test import generates new ID when original exists."""
        with patch('backend.export_import.save_conversation'):
            with patch('backend.export_import.get_conversation', return_value=sample_conversation):
                with patch('backend.export_import.validate_conversation_id'):
                    new_id, warnings = import_conversation_json(sample_export_data, preserve_id=True)

        assert new_id != sample_export_data["conversation"]["id"]
        assert any("exists" in w.lower() for w in warnings)


# =============================================================================
# Test Markdown Export
# =============================================================================

class TestExportConversationMarkdown:
    """Tests for Markdown export functionality."""

    def test_export_contains_title(self, sample_conversation):
        """Test Markdown export includes title."""
        with patch('backend.export_import.get_conversation', return_value=sample_conversation):
            with patch('backend.export_import.validate_conversation_id'):
                result = export_conversation_markdown(sample_conversation["id"])

        assert f"# {sample_conversation['title']}" in result

    def test_export_contains_metadata(self, sample_conversation):
        """Test Markdown export includes metadata section."""
        with patch('backend.export_import.get_conversation', return_value=sample_conversation):
            with patch('backend.export_import.validate_conversation_id'):
                result = export_conversation_markdown(sample_conversation["id"])

        assert "## Metadata" in result
        assert sample_conversation["id"] in result

    def test_export_contains_model_config(self, sample_conversation):
        """Test Markdown export includes model configuration."""
        with patch('backend.export_import.get_conversation', return_value=sample_conversation):
            with patch('backend.export_import.validate_conversation_id'):
                result = export_conversation_markdown(sample_conversation["id"])

        assert "Council Configuration" in result
        assert "openai:gpt-4" in result

    def test_export_contains_stages(self, sample_conversation):
        """Test Markdown export includes all stages."""
        with patch('backend.export_import.get_conversation', return_value=sample_conversation):
            with patch('backend.export_import.validate_conversation_id'):
                result = export_conversation_markdown(sample_conversation["id"])

        assert "Stage 1: Individual Responses" in result
        assert "Stage 2: Peer Rankings" in result
        assert "Stage 3: Final Answer" in result

    def test_export_contains_ranking_table(self, sample_conversation):
        """Test Markdown export includes ranking table."""
        with patch('backend.export_import.get_conversation', return_value=sample_conversation):
            with patch('backend.export_import.validate_conversation_id'):
                result = export_conversation_markdown(sample_conversation["id"])

        assert "| Rank | Response |" in result


# =============================================================================
# Test ZIP Manifest
# =============================================================================

class TestZipManifest:
    """Tests for ZipManifest dataclass."""

    def test_default_values(self):
        """Test manifest has correct defaults."""
        manifest = ZipManifest()

        assert manifest.export_version == EXPORT_VERSION
        assert manifest.source_application == "llm-council"
        assert manifest.conversation_count == 0
        assert manifest.conversations == []

    def test_to_dict(self):
        """Test manifest serialization."""
        manifest = ZipManifest(
            conversation_count=2,
            conversations=[
                {"id": "abc", "title": "Test 1"},
                {"id": "def", "title": "Test 2"}
            ]
        )
        result = manifest.to_dict()

        assert result["conversation_count"] == 2
        assert len(result["conversations"]) == 2


# =============================================================================
# Test ZIP Export
# =============================================================================

class TestExportConversationsZip:
    """Tests for ZIP export functionality."""

    def test_export_creates_valid_zip(self, sample_conversation):
        """Test ZIP export creates valid archive."""
        with patch('backend.export_import.list_conversations', return_value=[{"id": sample_conversation["id"]}]):
            with patch('backend.export_import.get_conversation', return_value=sample_conversation):
                with patch('backend.export_import.validate_conversation_id'):
                    zip_data = export_conversations_zip()

        # Should be valid ZIP
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            # Should contain manifest
            assert "manifest.json" in zf.namelist()

            # Should contain conversation files
            json_files = [f for f in zf.namelist() if f.endswith('.json') and f != 'manifest.json']
            assert len(json_files) > 0

    def test_export_includes_markdown(self, sample_conversation):
        """Test ZIP export includes Markdown when requested."""
        with patch('backend.export_import.list_conversations', return_value=[{"id": sample_conversation["id"]}]):
            with patch('backend.export_import.get_conversation', return_value=sample_conversation):
                with patch('backend.export_import.validate_conversation_id'):
                    zip_data = export_conversations_zip(include_markdown=True)

        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            md_files = [f for f in zf.namelist() if f.endswith('.md')]
            assert len(md_files) > 0

    def test_export_manifest_accurate(self, sample_conversation):
        """Test ZIP manifest contains accurate information."""
        with patch('backend.export_import.list_conversations', return_value=[{"id": sample_conversation["id"]}]):
            with patch('backend.export_import.get_conversation', return_value=sample_conversation):
                with patch('backend.export_import.validate_conversation_id'):
                    zip_data = export_conversations_zip()

        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            manifest = json.loads(zf.read("manifest.json"))

            assert manifest["conversation_count"] == 1
            assert len(manifest["conversations"]) == 1
            assert manifest["conversations"][0]["id"] == sample_conversation["id"]


# =============================================================================
# Test ZIP Import Validation
# =============================================================================

class TestValidateImportZip:
    """Tests for ZIP import validation."""

    def test_validate_valid_zip(self, sample_export_data):
        """Test validation of valid ZIP archive."""
        # Create test ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr(
                "conversations/test.json",
                json.dumps(sample_export_data)
            )
            zf.writestr(
                "manifest.json",
                json.dumps({"export_version": EXPORT_VERSION})
            )

        result = validate_import_zip(zip_buffer.getvalue())

        assert result.valid is True
        assert len(result.data["conversations"]) == 1

    def test_validate_invalid_zip(self):
        """Test validation fails for invalid ZIP."""
        result = validate_import_zip(b"not a zip file")

        assert result.valid is False
        assert any("zip" in e.lower() for e in result.errors)

    def test_validate_empty_zip(self):
        """Test validation fails for empty ZIP."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            pass  # Empty ZIP

        result = validate_import_zip(zip_buffer.getvalue())

        assert result.valid is False
        assert any("no" in e.lower() and "json" in e.lower() for e in result.errors)


# =============================================================================
# Test ZIP Import
# =============================================================================

class TestImportConversationsZip:
    """Tests for ZIP import functionality."""

    def test_import_valid_zip(self, sample_export_data):
        """Test importing valid ZIP archive."""
        # Create test ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr(
                "conversations/test.json",
                json.dumps(sample_export_data)
            )

        with patch('backend.export_import.save_conversation'):
            with patch('backend.export_import.get_conversation', return_value=None):
                imported_ids, warnings = import_conversations_zip(zip_buffer.getvalue())

        assert len(imported_ids) == 1

    def test_import_invalid_zip_raises(self):
        """Test import raises for invalid ZIP."""
        with pytest.raises(ValueError, match="Invalid ZIP"):
            import_conversations_zip(b"not a zip file")


# =============================================================================
# Test Utility Functions
# =============================================================================

class TestGetExportFilename:
    """Tests for filename generation."""

    def test_json_filename(self):
        """Test JSON filename generation."""
        with patch('backend.export_import.get_conversation', return_value={"title": "Test Title"}):
            filename = get_export_filename("550e8400-e29b-41d4-a716-446655440000", "json")

        assert filename.endswith(".json")
        assert "Test" in filename or "550e8400" in filename

    def test_zip_filename(self):
        """Test ZIP filename generation."""
        filename = get_export_filename("collection", "zip")

        assert filename.endswith(".zip")
        assert "export" in filename.lower()

    def test_sanitizes_title(self):
        """Test filename sanitizes special characters."""
        with patch('backend.export_import.get_conversation', return_value={"title": "Test/With:Special*Chars"}):
            filename = get_export_filename("550e8400-e29b-41d4-a716-446655440000", "json")

        # Should not contain special characters
        assert "/" not in filename
        assert ":" not in filename
        assert "*" not in filename
