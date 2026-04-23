from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from internal.application.errors import EventPublicationError
from internal.domain.services.event_publisher import EventPublisher
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
)


class RabbitMQCustomerValidationConsumer:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any],
        consumer_exchange: str,
        input_queue: str,
        handler: CustomerValidationConsumer,
        event_publisher: EventPublisher,
    ) -> None:
        self.connection_factory = connection_factory
        self.consumer_exchange = consumer_exchange
        self.input_queue = input_queue
        self._handler = handler
        self._event_publisher = event_publisher

    def ensure_topology(self) -> None:
        connection = self.connection_factory()
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=self.consumer_exchange,
                exchange_type="topic",
                durable=True,
            )
            channel.queue_declare(queue=self.input_queue, durable=True)
            channel.queue_bind(
                exchange=self.consumer_exchange,
                queue=self.input_queue,
                routing_key="BookingCreated",
            )
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def process_next_message(self) -> bool:
        connection = self.connection_factory()
        try:
            channel = connection.channel()
            method_frame, _, body = channel.basic_get(
                queue=self.input_queue,
                auto_ack=False,
            )
            if method_frame is None:
                return False

            payload = json.loads(body.decode())
            if not isinstance(payload, dict):
                channel.basic_nack(method_frame.delivery_tag, requeue=False)
                return True

            result = self._handler.handle(payload)
            if result.event is not None:
                try:
                    self._event_publisher.publish(result.event)
                except EventPublicationError:
                    channel.basic_nack(method_frame.delivery_tag, requeue=True)
                    return True

            if result.should_ack:
                channel.basic_ack(method_frame.delivery_tag)
                return True

            channel.basic_nack(method_frame.delivery_tag, requeue=result.requeue)
            return True
        finally:
            if hasattr(connection, "close"):
                connection.close()

    def start_consuming(self) -> None:
        while self.process_next_message():
            continue
