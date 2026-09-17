from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    """Metadata describing an approved LLM."""

    model_id: str
    provider: str
    open_weight: bool
    license: str
    free_hosted: bool
    supports_tools: bool
