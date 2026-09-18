from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator.service import OrchestrationService


def create_orchestration_service(
    session: AsyncSession,
) -> OrchestrationService:
    # The remaining concrete services are assembled here so the
    # FastAPI layer does not know about individual agent internals.
    #
    # This factory is intentionally the composition root. As modules
    # gain configuration, their construction belongs here rather than
    # inside OrchestrationService.

    raise NotImplementedError(
        "Orchestration dependency wiring will be completed in "
        "Module 17.4.2 after the concrete service constructors are "
        "verified."
    )
