from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from internal.application.errors import EventPublicationError
from internal.domain.services.event_publisher import EventPublisher
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
)

logger = logging.getLogger(__name__)


class RabbitMQCustomerValidationConsumer:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any],
        request_exchange: str,
        request_routing_key: str,
        input_queue: str,
        request_exchange_type: str = "direct",
        handler: CustomerValidationConsumer,
        event_publisher: EventPublisher,
    ) -> None:
        self.connection_factory = connection_factory
        self.request_exchange = request_exchange
        self.request_exchange_type = request_exchange_type
        self.request_routing_key = request_routing_key
        self.input_queue = input_queue
        self._handler = handler
        self._event_publisher = event_publisher

    def ensure_topology(self) -> None:
        connection = self.connection_factory()
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=self.request_exchange,
                exchange_type=self.request_exchange_type,
                durable=True,
            )
            channel.queue_declare(queue=self.input_queue, durable=True)
            channel.queue_bind(
                exchange=self.request_exchange,
                queue=self.input_queue,
                routing_key=self.request_routing_key,
            )
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def process_next_message(self) -> bool:
        connection = self.connection_factory()
        try:
            channel = connection.channel()
            return self._consume_once(channel)
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def start_consuming(
        self,
        *,
        idle_sleep_seconds: float = 0.5,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        resolved_sleep_fn = sleep_fn or time.sleep
        connection = self.connection_factory()
        try:
            channel = connection.channel()
            while True:
                processed = self._consume_once(channel)
                if not processed:
                    resolved_sleep_fn(idle_sleep_seconds)
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def _consume_once(self, channel: Any) -> bool:
        method_frame, _, body = channel.basic_get(
            queue=self.input_queue,
            auto_ack=False,
        )
        if method_frame is None:
            return False
        return self._process_delivery(channel=channel, method_frame=method_frame, body=body)

    def _process_delivery(self, *, channel: Any, method_frame: Any, body: Any) -> bool:
        try:
            body_text = body.decode()
            payload = json.loads(body_text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning(
                "Discarding customer validation message due to invalid JSON delivery_tag=%s",
                method_frame.delivery_tag,
            )
            channel.basic_nack(method_frame.delivery_tag, requeue=False)
            logger.info(
                "Customer validation ack decision=nack requeue=false delivery_tag=%s",
                method_frame.delivery_tag,
            )
            return True

        logger.info(
            "Received customer validation worker message delivery_tag=%s payload=%s",
            method_frame.delivery_tag,
            _payload_log_subset(payload),
        )
        if not isinstance(payload, dict):
            channel.basic_nack(method_frame.delivery_tag, requeue=False)
            logger.warning(
                "Discarding customer validation message because payload is not an object delivery_tag=%s payload_type=%s",
                method_frame.delivery_tag,
                type(payload).__name__,
            )
            logger.info(
                "Customer validation ack decision=nack requeue=false delivery_tag=%s",
                method_frame.delivery_tag,
            )
            return True

        result = self._handler.handle(payload)
        logger.info(
            "Customer validation handled delivery_tag=%s should_ack=%s requeue=%s has_event=%s",
            method_frame.delivery_tag,
            result.should_ack,
            result.requeue,
            result.event is not None,
        )
        if result.event is not None:
            try:
                logger.info(
                    "Publishing customer validation result delivery_tag=%s event_type=%s booking_id=%s customer_id=%s is_valid=%s",
                    method_frame.delivery_tag,
                    result.event.event_type,
                    result.event.booking_id,
                    result.event.customer_id,
                    result.event.is_valid,
                )
                self._event_publisher.publish(result.event)
                logger.info(
                    "Published customer validation result delivery_tag=%s event_type=%s",
                    method_frame.delivery_tag,
                    result.event.event_type,
                )
            except EventPublicationError:
                channel.basic_nack(method_frame.delivery_tag, requeue=True)
                logger.exception(
                    "Failed publishing customer validation result delivery_tag=%s decision=nack requeue=true",
                    method_frame.delivery_tag,
                )
                return True

        if result.should_ack:
            channel.basic_ack(method_frame.delivery_tag)
            logger.info(
                "Customer validation ack decision=ack requeue=false delivery_tag=%s",
                method_frame.delivery_tag,
            )
            return True

        channel.basic_nack(method_frame.delivery_tag, requeue=result.requeue)
        logger.info(
            "Customer validation ack decision=nack requeue=%s delivery_tag=%s",
            result.requeue,
            method_frame.delivery_tag,
        )
        return True


def _payload_log_subset(payload: object) -> dict[str, object | None]:
    if not isinstance(payload, dict):
        return {"rawType": type(payload).__name__}
    return {
        "eventId": payload.get("eventId"),
        "eventType": payload.get("eventType"),
        "bookingId": payload.get("bookingId"),
        "customerId": payload.get("customerId"),
        "timestamp": payload.get("timestamp"),
    }
