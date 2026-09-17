class PlannerError(Exception):
    """Base exception for planner errors."""


class PlannerConfigurationError(PlannerError):
    """Raised when planner configuration is invalid."""


class PlanningContextError(PlannerError):
    """Raised when planning context cannot be constructed."""
