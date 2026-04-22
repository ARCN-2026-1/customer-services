from typing import Protocol


class TokenGenerator(Protocol):
    def generate(self, *, customer_id: str, role: str) -> str: ...

    def validate(self, token: str) -> dict[str, str]: ...
