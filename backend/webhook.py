"""Webhook notifications for council events."""

import asyncio
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import httpx

from .logger import get_logger


class WebhookEvent(str, Enum):
    """Webhook event types."""
    CONVERSATION_CREATED = "conversation.created"
    STAGE1_COMPLETE = "stage1.complete"
    STAGE2_COMPLETE = "stage2.complete"
    STAGE3_COMPLETE = "stage3.complete"
    COUNCIL_COMPLETE = "council.complete"
    COUNCIL_ERROR = "council.error"


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    url: Optional[str] = None
    secret: Optional[str] = None
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "WebhookConfig":
        """
        Load webhook configuration from environment variables.

        Environment variables:
            WEBHOOK_URL: The URL to send webhook events to
            WEBHOOK_SECRET: The secret used to sign webhook payloads

        Returns:
            WebhookConfig instance
        """
        url = os.getenv("WEBHOOK_URL", "").strip() or None
        secret = os.getenv("WEBHOOK_SECRET", "").strip() or None

        return cls(
            url=url,
            secret=secret,
            enabled=url is not None
        )


@dataclass
class WebhookPayload:
    """Structured webhook payload."""
    event: str
    timestamp: str
    conversation_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert payload to dictionary."""
        return {
            "event": self.event,
            "timestamp": self.timestamp,
            "conversation_id": self.conversation_id,
            "data": self.data
        }

    def to_json(self) -> str:
        """Convert payload to JSON string."""
        return json.dumps(self.to_dict(), separators=(',', ':'), sort_keys=True)


def calculate_signature(payload_json: str, secret: str) -> str:
    """
    Calculate HMAC-SHA256 signature for a webhook payload.

    Args:
        payload_json: JSON string of the payload
        secret: Secret key for signing

    Returns:
        Hex-encoded HMAC-SHA256 signature
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def build_payload(
    event: WebhookEvent,
    conversation_id: str,
    data: Optional[Dict[str, Any]] = None
) -> WebhookPayload:
    """
    Build a webhook payload.

    Args:
        event: The webhook event type
        conversation_id: UUID of the conversation
        data: Optional event-specific data

    Returns:
        WebhookPayload instance
    """
    return WebhookPayload(
        event=event.value,
        timestamp=datetime.now(timezone.utc).isoformat(),
        conversation_id=conversation_id,
        data=data or {}
    )


class WebhookDeliveryWorker:
    """Async webhook delivery worker with retry logic."""

    # Retry delays in seconds: 1s, 2s, 4s
    RETRY_DELAYS = [1, 2, 4]
    MAX_ATTEMPTS = 3
    TIMEOUT_SECONDS = 10

    def __init__(self, config: WebhookConfig):
        """
        Initialize webhook delivery worker.

        Args:
            config: Webhook configuration
        """
        self.config = config
        self.logger = get_logger()
        self._pending_tasks: List[asyncio.Task] = []

    async def deliver(
        self,
        payload: WebhookPayload,
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        Deliver a webhook payload with retry logic.

        Args:
            payload: The webhook payload to deliver
            webhook_url: Optional per-request URL override

        Returns:
            True if delivery succeeded, False otherwise
        """
        url = webhook_url or self.config.url

        if not url:
            self.logger.debug("Webhook delivery skipped - no URL configured")
            return False

        payload_json = payload.to_json()

        # Calculate signature if secret is configured
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": payload.event,
        }

        if self.config.secret:
            signature = calculate_signature(payload_json, self.config.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # Attempt delivery with retries
        for attempt in range(self.MAX_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        url,
                        content=payload_json,
                        headers=headers
                    )

                    if response.is_success:
                        self.logger.info(
                            "Webhook delivered successfully",
                            event=payload.event,
                            conversation_id=payload.conversation_id,
                            attempt=attempt + 1,
                            status_code=response.status_code
                        )
                        return True

                    # Non-2xx response
                    self.logger.warn(
                        "Webhook delivery failed with non-2xx response",
                        event=payload.event,
                        conversation_id=payload.conversation_id,
                        attempt=attempt + 1,
                        status_code=response.status_code
                    )

            except Exception as e:
                self.logger.warn(
                    "Webhook delivery failed with error",
                    event=payload.event,
                    conversation_id=payload.conversation_id,
                    attempt=attempt + 1,
                    error=str(e)
                )

            # If not the last attempt, wait before retrying
            if attempt < self.MAX_ATTEMPTS - 1:
                delay = self.RETRY_DELAYS[attempt]
                self.logger.debug(
                    "Retrying webhook delivery",
                    event=payload.event,
                    delay_seconds=delay,
                    next_attempt=attempt + 2
                )
                await asyncio.sleep(delay)

        # All attempts failed
        self.logger.error(
            "Webhook delivery failed after all retries",
            event=payload.event,
            conversation_id=payload.conversation_id,
            max_attempts=self.MAX_ATTEMPTS
        )
        return False

    def deliver_async(
        self,
        payload: WebhookPayload,
        webhook_url: Optional[str] = None
    ) -> None:
        """
        Schedule webhook delivery as a background task.

        This method returns immediately and does not block the caller.
        Delivery happens asynchronously with retries.

        Args:
            payload: The webhook payload to deliver
            webhook_url: Optional per-request URL override
        """
        if not self.config.enabled and not webhook_url:
            return

        task = asyncio.create_task(self.deliver(payload, webhook_url))

        # Track task to prevent garbage collection
        self._pending_tasks.append(task)

        # Clean up completed tasks
        self._pending_tasks = [t for t in self._pending_tasks if not t.done()]

    async def wait_pending(self) -> None:
        """Wait for all pending deliveries to complete."""
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()


# Global webhook worker instance
_webhook_worker: Optional[WebhookDeliveryWorker] = None


def get_webhook_worker() -> WebhookDeliveryWorker:
    """
    Get or create global webhook worker instance.

    Returns:
        WebhookDeliveryWorker instance
    """
    global _webhook_worker
    if _webhook_worker is None:
        config = WebhookConfig.from_env()
        _webhook_worker = WebhookDeliveryWorker(config)
    return _webhook_worker


def get_webhook_config() -> WebhookConfig:
    """
    Get the current webhook configuration.

    Returns:
        WebhookConfig instance
    """
    return get_webhook_worker().config


def emit_webhook(
    event: WebhookEvent,
    conversation_id: str,
    data: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None
) -> None:
    """
    Emit a webhook event asynchronously.

    This is the main entry point for emitting webhooks from the application.
    It builds the payload and schedules delivery as a background task.

    Args:
        event: The webhook event type
        conversation_id: UUID of the conversation
        data: Optional event-specific data
        webhook_url: Optional per-conversation URL override
    """
    worker = get_webhook_worker()
    payload = build_payload(event, conversation_id, data)
    worker.deliver_async(payload, webhook_url)
