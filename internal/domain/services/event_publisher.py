from typing import Protocol


class EventPublisher(Protocol):
    def publish(self, event: object) -> None: ...
