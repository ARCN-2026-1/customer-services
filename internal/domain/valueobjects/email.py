from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("Customer email must be a valid email")

        local_part, _, domain = normalized.partition("@")
        if not local_part or "." not in domain:
            raise ValueError("Customer email must be a valid email")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
