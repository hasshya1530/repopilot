class ImplementationValidationError(RuntimeError):
    """Raised when generated implementation changes violate the approved plan."""

    def __init__(self, message: str, *, errors: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.errors = errors
