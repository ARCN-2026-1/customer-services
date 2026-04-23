from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from internal.application.errors import EventPublicationError

logger = logging.getLogger(__name__)


def _to_camel_case(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _serialize_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _event_to_payload(event: object) -> dict[str, Any]:
    if not is_dataclass(event) or isinstance(event, type):
        raise TypeError("RabbitMQEventPublisher only supports dataclass events")

    raw_payload = asdict(cast(Any, event))
    return {
        _to_camel_case(key): _serialize_value(value)
        for key, value in raw_payload.items()
    }


def _resolve_event_name(payload: dict[str, Any]) -> str:
    event_name = payload.get("eventName")
    if isinstance(event_name, str) and event_name:
        return event_name

    event_type = payload.get("eventType")
    if isinstance(event_type, str) and event_type:
        return event_type

    raise KeyError("eventType")


class RabbitMQEventPublisher:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any],
        exchange_name: str,
        exchange_type: str = "topic",
        routing_key: str | None = None,
        properties_factory: Any | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._routing_key = routing_key
        self._properties_factory = properties_factory or _build_message_properties

    def publish(self, event: object) -> None:
        payload = _event_to_payload(event)
        event_name = _resolve_event_name(payload)
        routing_key = self._routing_key or event_name
        connection = self._connection_factory()
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=self._exchange_name,
                exchange_type=self._exchange_type,
                durable=True,
            )
            channel.basic_publish(
                exchange=self._exchange_name,
                routing_key=routing_key,
                body=json.dumps(payload),
                properties=self._properties_factory(event_name=event_name),
            )
        except Exception as error:
            logger.exception(
                (
                    "Failed to publish customer event to RabbitMQ "
                    "event_name=%s exchange=%s"
                ),
                event_name,
                self._exchange_name,
            )
            raise EventPublicationError("Customer event publication failed") from error
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def close(self) -> None:
        return None


def _build_message_properties(*, event_name: str) -> Any:
    import pika

    return pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,
        type=event_name,
    )
