from typing import Protocol


class PaymentAdapter(Protocol):
    """Provider interface: activation must follow a verified provider event."""

    name: str

    def enabled(self) -> bool: ...
