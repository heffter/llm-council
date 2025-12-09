"""Unit tests for storage_utils module."""

import pytest
from uuid import UUID
from pathlib import Path
from backend.storage_utils import (
    validate_conversation_id,
    get_safe_conversation_path,
    truncate_for_storage,
    InvalidConversationIdError,
    PathTraversalError
)


class TestValidateConversationId:
    """Tests for validate_conversation_id function."""

    def test_valid_uuid_v4(self, valid_uuid):
        """Valid UUID v4 should pass validation."""
        # Should not raise any exception
        validate_conversation_id(valid_uuid)

    def test_invalid_format_raises_error(self):
        """Invalid UUID format should raise InvalidConversationIdError."""
        with pytest.raises(InvalidConversationIdError):
            validate_conversation_id("not-a-uuid")

    def test_non_canonical_format_raises_error(self):
        """Non-canonical UUID format should raise InvalidConversationIdError."""
        # Valid UUID but uppercase - not canonical
        uuid_upper = "12345678-1234-4234-B234-123456789ABC"
        with pytest.raises(InvalidConversationIdError):
            validate_conversation_id(uuid_upper)

    def test_uuid_v3_raises_error(self):
        """UUID v3 should be rejected, only v4 accepted."""
        uuid_v3 = "00000000-0000-3000-0000-000000000000"
        with pytest.raises(InvalidConversationIdError):
            validate_conversation_id(uuid_v3)

    def test_empty_string_raises_error(self):
        """Empty string should raise InvalidConversationIdError."""
        with pytest.raises(InvalidConversationIdError):
            validate_conversation_id("")

    def test_path_traversal_attempt_raises_error(self):
        """Path traversal strings should raise InvalidConversationIdError."""
        with pytest.raises(InvalidConversationIdError):
            validate_conversation_id("../../../etc/passwd")


class TestGetSafeConversationPath:
    """Tests for get_safe_conversation_path function."""

    def test_valid_uuid_returns_safe_path(self, valid_uuid, temp_data_dir):
        """Valid UUID should return path within base directory."""
        path = get_safe_conversation_path(valid_uuid, temp_data_dir)

        # Path should be within base directory
        assert path.startswith(str(Path(temp_data_dir).resolve()))
        # Path should end with .json
        assert path.endswith('.json')
        # Filename should be the UUID
        assert valid_uuid in path

    def test_invalid_uuid_raises_error(self, temp_data_dir):
        """Invalid UUID should raise InvalidConversationIdError."""
        with pytest.raises(InvalidConversationIdError):
            get_safe_conversation_path("not-a-uuid", temp_data_dir)

    def test_path_traversal_prevented(self, temp_data_dir):
        """Path traversal attempts should be prevented."""
        # Even if somehow a traversal string got validated, the path check should catch it
        with pytest.raises(InvalidConversationIdError):
            get_safe_conversation_path("../evil", temp_data_dir)

    def test_path_stays_within_base_directory(self, valid_uuid, temp_data_dir):
        """Returned path must stay within base directory."""
        path = get_safe_conversation_path(valid_uuid, temp_data_dir)

        base_path = Path(temp_data_dir).resolve()
        result_path = Path(path).resolve()

        # Ensure result is relative to base (no PathTraversalError)
        try:
            result_path.relative_to(base_path)
        except ValueError:
            pytest.fail("Path escaped base directory")


class TestTruncateForStorage:
    """Tests for truncate_for_storage function."""

    def test_short_text_unchanged(self):
        """Text shorter than limit should be returned unchanged."""
        text = "Hello, world!"
        result = truncate_for_storage(text, max_bytes=1000)
        assert result == text

    def test_long_text_truncated(self):
        """Text longer than limit should be truncated."""
        text = "A" * 1000
        result = truncate_for_storage(text, max_bytes=100)

        # Result should be shorter
        assert len(result.encode('utf-8')) <= 100 + len('\n[TRUNCATED]'.encode('utf-8'))
        # Should have truncation marker
        assert result.endswith('[TRUNCATED]')

    def test_exact_limit_unchanged(self):
        """Text exactly at limit should be unchanged."""
        text = "A" * 100
        result = truncate_for_storage(text, max_bytes=100)
        assert result == text

    def test_utf8_boundary_safety(self):
        """Truncation should not break UTF-8 characters."""
        # String with multi-byte UTF-8 characters
        text = "Hello 🌍🌎🌏 " * 100  # emoji are 4 bytes each
        result = truncate_for_storage(text, max_bytes=50)

        # Result should be valid UTF-8 (no decode errors)
        try:
            result.encode('utf-8')
        except UnicodeEncodeError:
            pytest.fail("Truncation broke UTF-8 encoding")

        # Should have truncation marker
        assert '[TRUNCATED]' in result

    def test_default_limit(self):
        """Default limit should be 256KB."""
        text = "A" * 300000  # 300KB
        result = truncate_for_storage(text)  # Use default

        # Should be truncated
        assert len(result) < len(text)
        assert '[TRUNCATED]' in result

    def test_custom_limit(self):
        """Custom limit should be respected."""
        text = "A" * 1000
        custom_limit = 200
        result = truncate_for_storage(text, max_bytes=custom_limit)

        # Should respect custom limit
        encoded_result = result.encode('utf-8')
        # Allow some buffer for truncation marker
        assert len(encoded_result) <= custom_limit + 50
        assert '[TRUNCATED]' in result

    def test_empty_string(self):
        """Empty string should be handled gracefully."""
        result = truncate_for_storage("", max_bytes=100)
        assert result == ""

    def test_newline_before_marker(self):
        """Truncation marker should be preceded by newline."""
        text = "A" * 1000
        result = truncate_for_storage(text, max_bytes=100)

        if '[TRUNCATED]' in result:
            assert '\n[TRUNCATED]' in result
