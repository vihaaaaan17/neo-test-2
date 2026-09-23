class ResearchExecutionError(Exception):
    """Base class for research execution errors."""
    pass

class ResearchEngineSetupError(ResearchExecutionError):
    """Raised when an engine cannot be instantiated due to missing dependencies or config."""
    pass

class TokenLimitExceededError(ResearchExecutionError):
    """Raised when token limits are exceeded."""
    pass
