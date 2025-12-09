"""Pytest configuration and shared fixtures."""

import pytest
import uuid
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def valid_uuid():
    """Generate a valid UUID v4."""
    return str(uuid.uuid4())


@pytest.fixture
def invalid_uuids():
    """Collection of invalid UUID strings."""
    return [
        "not-a-uuid",
        "123",
        "",
        "12345678-1234-1234-1234-123456789012",  # Valid format but not canonical
        "../../../etc/passwd",
        "00000000-0000-3000-0000-000000000000",  # UUID v3, not v4
    ]


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Factory for setting environment variables in tests."""
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
    return _set_env


@pytest.fixture
def sample_llm_response():
    """Sample LLM API response."""
    return {
        "content": "This is a test response from the LLM.",
        "model": "test-model",
        "usage": {"input_tokens": 10, "output_tokens": 20}
    }


@pytest.fixture
def sample_messages():
    """Sample message list for LLM requests."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
