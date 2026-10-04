"""Notification provider boundaries and built-in provider implementations."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from time import perf_counter
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from manga_director.notifications.models import NotificationMessage, NotificationResult

LOGGER = logging.getLogger(__name__)


class NotificationProvider(Protocol):
    """Boundary implemented by notification delivery adapters."""

    def send(self, message: NotificationMessage) -> NotificationResult:
        """Deliver one notification message."""


class ConsoleNotificationProvider:
    """Log notifications without exposing their potentially sensitive content."""

    name = "console"

    def send(self, message: NotificationMessage) -> NotificationResult:
        LOGGER.info(
            "notification delivered event=%s message_id=%s",
            message.event_type,
            message.id,
        )
        return NotificationResult(
            success=True,
            provider=self.name,
            message_id=message.id,
        )


class MockNotificationProvider:
    """Deterministic provider used by unit tests and local development."""

    name = "mock"

    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.sent: list[NotificationMessage] = []

    def send(self, message: NotificationMessage) -> NotificationResult:
        self.sent.append(message)
        return NotificationResult(
            success=self.success,
            provider=self.name,
            message_id=message.id,
            errors=[] if self.success else ["mock failure"],
        )


class _NoRedirect(HTTPRedirectHandler):
    """Prevent a validated HTTPS URL from redirecting to an unsafe target."""

    def redirect_request(self, *args: object, **kwargs: object) -> Request | None:
        return None


class WebhookNotificationProvider:
    """Signed HTTPS webhook adapter with basic SSRF protections."""

    name = "webhook"

    def __init__(
        self,
        url: str,
        *,
        secret: str,
        timeout: float = 5.0,
        allowed_hosts: set[str] | None = None,
        block_private_networks: bool = True,
    ) -> None:
        self._url = url
        self._secret = secret
        self._timeout = timeout
        self._hosts = allowed_hosts
        self._block_private = block_private_networks
        self._validate()

    def _validate(self) -> None:
        parsed = urlparse(self._url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or (self._hosts is not None and parsed.hostname not in self._hosts)
        ):
            raise ValueError("Webhook URL must be an allowed HTTPS URL")

        if not self._block_private:
            return

        for _, _, _, _, address in socket.getaddrinfo(parsed.hostname, None):
            resolved = ipaddress.ip_address(address[0])
            if resolved.is_private or resolved.is_loopback:
                raise ValueError("Webhook host resolves to a private address")

    def send(self, message: NotificationMessage) -> NotificationResult:
        started = perf_counter()
        payload = json.dumps(message.model_dump(mode="json"), separators=(",", ":")).encode()
        timestamp = str(int(message.created_at.timestamp()))
        signature = hmac.new(
            self._secret.encode(),
            f"{timestamp}.".encode() + payload,
            hashlib.sha256,
        ).hexdigest()
        request = Request(
            self._url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Manga-Timestamp": timestamp,
                "X-Manga-Signature": f"sha256={signature}",
                "X-Manga-Event-Id": message.id,
            },
        )

        try:
            response = build_opener(_NoRedirect()).open(request, timeout=self._timeout)
            status = response.status
            response.read(65_536)
            return NotificationResult(
                success=200 <= status < 300,
                provider=self.name,
                message_id=message.id,
                status_code=status,
                elapsed_time=perf_counter() - started,
            )
        except HTTPError as exc:
            return NotificationResult(
                success=False,
                provider=self.name,
                message_id=message.id,
                status_code=exc.code,
                elapsed_time=perf_counter() - started,
                errors=[str(exc)],
            )
        except (URLError, OSError) as exc:
            return NotificationResult(
                success=False,
                provider=self.name,
                message_id=message.id,
                elapsed_time=perf_counter() - started,
                errors=[str(exc)],
            )
