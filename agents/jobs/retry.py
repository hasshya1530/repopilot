from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must not be negative.")

        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be greater than or equal to "
                "base_delay_seconds."
            )

    def delay_for_attempt(self, attempt: int) -> float:
        if attempt < 0:
            raise ValueError("attempt must not be negative.")

        delay: float = self.base_delay_seconds * float(2**attempt)

        return min(delay, self.max_delay_seconds)
