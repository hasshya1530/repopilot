from agents.llm.policy.models import ModelDefinition

OLLAMA_MODELS: dict[str, ModelDefinition] = {
    "qwen2.5-coder:3b": ModelDefinition(
        model_id="qwen2.5-coder:3b",
        provider="ollama",
        open_weight=True,
        license="Qwen Research License",
        free_hosted=False,
        supports_tools=True,
    ),
}


OPENROUTER_MODELS: dict[str, ModelDefinition] = {
    "nvidia/nemotron-3.5-lightning:free": ModelDefinition(
        model_id="nvidia/nemotron-3.5-lightning:free",
        provider="openrouter",
        open_weight=True,
        license="NVIDIA Open License",
        free_hosted=True,
        supports_tools=True,
    ),
    "nvidia/nemotron-3-ultra-550b-a55b:free": ModelDefinition(
        model_id="nvidia/nemotron-3-ultra-550b-a55b:free",
        provider="openrouter",
        open_weight=True,
        license="NVIDIA Open License",
        free_hosted=True,
        supports_tools=True,
    ),
}


def get_model_definition(
    provider: str,
    model_id: str,
) -> ModelDefinition | None:
    if provider == "ollama":
        return OLLAMA_MODELS.get(model_id)

    if provider == "openrouter":
        return OPENROUTER_MODELS.get(model_id)

    return None
