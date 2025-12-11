"""Tests for webhook module."""

import asyncio
import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.webhook import (
    WebhookConfig,
    WebhookEvent,
    WebhookPayload,
    WebhookDeliveryWorker,
    calculate_signature,
    build_payload,
    emit_webhook,
    get_webhook_config,
    get_webhook_worker,
)


class TestWebhookConfig:
    """Tests for WebhookConfig."""

    def test_from_env_with_values(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("WEBHOOK_URL", "https://example.com/webhook")
        monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")

        # Reset the global worker to pick up new env
        import backend.webhook as webhook_module
        webhook_module._webhook_worker = None

        config = WebhookConfig.from_env()

        assert config.url == "https://example.com/webhook"
        assert config.secret == "test-secret"
        assert config.enabled is True

    def test_from_env_without_values(self, monkeypatch):
        """Test loading config when env vars are not set."""
        monkeypatch.delenv("WEBHOOK_URL", raising=False)
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

        config = WebhookConfig.from_env()

        assert config.url is None
        assert config.secret is None
        assert config.enabled is False

    def test_from_env_with_empty_values(self, monkeypatch):
        """Test loading config when env vars are empty strings."""
        monkeypatch.setenv("WEBHOOK_URL", "  ")
        monkeypatch.setenv("WEBHOOK_SECRET", "")

        config = WebhookConfig.from_env()

        assert config.url is None
        assert config.secret is None
        assert config.enabled is False


class TestWebhookPayload:
    """Tests for WebhookPayload."""

    def test_to_dict(self):
        """Test payload conversion to dict."""
        payload = WebhookPayload(
            event="test.event",
            timestamp="2024-01-01T00:00:00Z",
            conversation_id="test-id",
            data={"key": "value"}
        )

        result = payload.to_dict()

        assert result == {
            "event": "test.event",
            "timestamp": "2024-01-01T00:00:00Z",
            "conversation_id": "test-id",
            "data": {"key": "value"}
        }

    def test_to_json_deterministic(self):
        """Test payload JSON is deterministic (sorted keys, no spaces)."""
        payload = WebhookPayload(
            event="test.event",
            timestamp="2024-01-01T00:00:00Z",
            conversation_id="test-id",
            data={"b": 2, "a": 1}
        )

        json_str = payload.to_json()

        # Should be sorted and compact
        assert '"a":1' in json_str
        assert '"b":2' in json_str
        assert json_str.index('"a"') < json_str.index('"b"')


class TestCalculateSignature:
    """Tests for HMAC signature calculation."""

    def test_calculate_signature(self):
        """Test HMAC-SHA256 signature calculation."""
        payload_json = '{"event":"test"}'
        secret = "my-secret"

        signature = calculate_signature(payload_json, secret)

        # Verify it's a valid hex string
        assert len(signature) == 64
        assert all(c in '0123456789abcdef' for c in signature)

        # Verify the signature is correct
        expected = hmac.new(
            secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        assert signature == expected

    def test_signature_deterministic(self):
        """Test that signatures are deterministic."""
        payload_json = '{"data":"test"}'
        secret = "secret123"

        sig1 = calculate_signature(payload_json, secret)
        sig2 = calculate_signature(payload_json, secret)

        assert sig1 == sig2

    def test_different_secrets_different_signatures(self):
        """Test that different secrets produce different signatures."""
        payload_json = '{"data":"test"}'

        sig1 = calculate_signature(payload_json, "secret1")
        sig2 = calculate_signature(payload_json, "secret2")

        assert sig1 != sig2


class TestBuildPayload:
    """Tests for payload building."""

    def test_build_payload_basic(self):
        """Test building a basic payload."""
        payload = build_payload(
            WebhookEvent.CONVERSATION_CREATED,
            "conv-123"
        )

        assert payload.event == "conversation.created"
        assert payload.conversation_id == "conv-123"
        assert payload.data == {}
        assert payload.timestamp  # Should have timestamp

    def test_build_payload_with_data(self):
        """Test building a payload with data."""
        payload = build_payload(
            WebhookEvent.COUNCIL_COMPLETE,
            "conv-456",
            data={"model_count": 3, "chairman": "gpt-4"}
        )

        assert payload.event == "council.complete"
        assert payload.conversation_id == "conv-456"
        assert payload.data == {"model_count": 3, "chairman": "gpt-4"}


class TestWebhookDeliveryWorker:
    """Tests for WebhookDeliveryWorker."""

    @pytest.fixture
    def worker(self):
        """Create a worker with test config."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True
        )
        return WebhookDeliveryWorker(config)

    @pytest.fixture
    def payload(self):
        """Create a test payload."""
        return WebhookPayload(
            event="test.event",
            timestamp="2024-01-01T00:00:00Z",
            conversation_id="test-conv",
            data={"key": "value"}
        )

    @pytest.mark.asyncio
    async def test_deliver_success(self, worker, payload):
        """Test successful webhook delivery."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = await worker.deliver(payload)

            assert result is True
            mock_client.post.assert_called_once()

            # Verify signature header was included
            call_kwargs = mock_client.post.call_args[1]
            assert "X-Webhook-Signature" in call_kwargs["headers"]
            assert call_kwargs["headers"]["X-Webhook-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_deliver_without_secret(self, payload):
        """Test delivery without secret (no signature header)."""
        config = WebhookConfig(
            url="https://example.com/webhook",
            secret=None,
            enabled=True
        )
        worker = WebhookDeliveryWorker(config)

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = await worker.deliver(payload)

            assert result is True
            call_kwargs = mock_client.post.call_args[1]
            assert "X-Webhook-Signature" not in call_kwargs["headers"]

    @pytest.mark.asyncio
    async def test_deliver_no_url_configured(self, payload):
        """Test delivery when no URL is configured."""
        config = WebhookConfig(url=None, secret=None, enabled=False)
        worker = WebhookDeliveryWorker(config)

        result = await worker.deliver(payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_deliver_with_url_override(self, worker, payload):
        """Test delivery with per-request URL override."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = await worker.deliver(payload, webhook_url="https://override.com/hook")

            assert result is True
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://override.com/hook"

    @pytest.mark.asyncio
    async def test_deliver_retry_on_failure(self, worker, payload):
        """Test retry logic on failures."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # First two calls fail, third succeeds
            mock_fail = MagicMock()
            mock_fail.is_success = False
            mock_fail.status_code = 500

            mock_success = MagicMock()
            mock_success.is_success = True
            mock_success.status_code = 200

            mock_client.post.side_effect = [mock_fail, mock_fail, mock_success]

            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.deliver(payload)

            assert result is True
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_deliver_all_retries_fail(self, worker, payload):
        """Test when all retries fail."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_fail = MagicMock()
            mock_fail.is_success = False
            mock_fail.status_code = 500
            mock_client.post.return_value = mock_fail

            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.deliver(payload)

            assert result is False
            assert mock_client.post.call_count == 3  # MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_deliver_network_error_retry(self, worker, payload):
        """Test retry on network errors."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_success = MagicMock()
            mock_success.is_success = True
            mock_success.status_code = 200

            # Network error then success
            mock_client.post.side_effect = [
                Exception("Connection refused"),
                mock_success
            ]

            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.deliver(payload)

            assert result is True
            assert mock_client.post.call_count == 2

    def test_deliver_async_schedules_task(self, worker, payload):
        """Test that deliver_async schedules a background task."""
        with patch.object(worker, 'deliver', new_callable=AsyncMock) as mock_deliver:
            with patch('asyncio.create_task') as mock_create_task:
                worker.deliver_async(payload)

                mock_create_task.assert_called_once()

    def test_deliver_async_skipped_when_disabled(self, payload):
        """Test that deliver_async is skipped when webhooks are disabled."""
        config = WebhookConfig(url=None, secret=None, enabled=False)
        worker = WebhookDeliveryWorker(config)

        with patch('asyncio.create_task') as mock_create_task:
            worker.deliver_async(payload)

            mock_create_task.assert_not_called()


class TestWebhookEvents:
    """Tests for webhook event types."""

    def test_all_events_defined(self):
        """Test that all expected events are defined."""
        expected_events = [
            "conversation.created",
            "stage1.complete",
            "stage2.complete",
            "stage3.complete",
            "council.complete",
            "council.error",
        ]

        actual_events = [e.value for e in WebhookEvent]

        assert set(expected_events) == set(actual_events)


class TestGlobalFunctions:
    """Tests for global webhook functions."""

    def test_get_webhook_worker_returns_singleton(self, monkeypatch):
        """Test that get_webhook_worker returns a singleton."""
        monkeypatch.setenv("WEBHOOK_URL", "https://test.com")
        monkeypatch.setenv("WEBHOOK_SECRET", "secret")

        import backend.webhook as webhook_module
        webhook_module._webhook_worker = None

        worker1 = get_webhook_worker()
        worker2 = get_webhook_worker()

        assert worker1 is worker2

    def test_get_webhook_config(self, monkeypatch):
        """Test get_webhook_config returns correct config."""
        monkeypatch.setenv("WEBHOOK_URL", "https://test.com/hook")
        monkeypatch.setenv("WEBHOOK_SECRET", "my-secret")

        import backend.webhook as webhook_module
        webhook_module._webhook_worker = None

        config = get_webhook_config()

        assert config.url == "https://test.com/hook"
        assert config.secret == "my-secret"
        assert config.enabled is True
