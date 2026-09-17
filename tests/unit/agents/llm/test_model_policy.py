from agents.llm.policy import get_model_definition


def test_qwen_model_is_registered() -> None:
    definition = get_model_definition(
        "ollama",
        "qwen2.5-coder:3b",
    )

    assert definition is not None
    assert definition.model_id == "qwen2.5-coder:3b"
    assert definition.provider == "ollama"
    assert definition.open_weight is True
    assert definition.license == "Qwen Research License"
    assert definition.free_hosted is False
    assert definition.supports_tools is True


def test_unknown_ollama_model_is_not_approved() -> None:
    definition = get_model_definition(
        "ollama",
        "some-random-model",
    )

    assert definition is None


def test_openrouter_lightning_is_registered() -> None:
    definition = get_model_definition(
        "openrouter",
        "nvidia/nemotron-3.5-lightning:free",
    )

    assert definition is not None
    assert definition.model_id == "nvidia/nemotron-3.5-lightning:free"
    assert definition.provider == "openrouter"
    assert definition.open_weight is True
    assert definition.free_hosted is True
    assert definition.supports_tools is True


def test_openrouter_ultra_is_registered() -> None:
    definition = get_model_definition(
        "openrouter",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
    )

    assert definition is not None
    assert definition.model_id == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert definition.provider == "openrouter"
    assert definition.open_weight is True
    assert definition.free_hosted is True
    assert definition.supports_tools is True


def test_unknown_openrouter_model_is_not_approved() -> None:
    definition = get_model_definition(
        "openrouter",
        "some-random-model:free",
    )

    assert definition is None


def test_unknown_provider_is_not_approved() -> None:
    definition = get_model_definition(
        "unknown-provider",
        "qwen2.5-coder:3b",
    )

    assert definition is None
