class ModelPolicyError(Exception):
    """Base exception for model policy violations."""


class UnsupportedModelError(ModelPolicyError):
    """Raised when a configured model is not approved."""


class UnsupportedProviderError(ModelPolicyError):
    """Raised when a configured provider is not supported."""
