class IndexingError(Exception):
    """Base exception for repository indexing failures."""


class IndexingConfigurationError(IndexingError):
    """Raised when indexing is configured incorrectly."""


class IndexingFileError(IndexingError):
    """Raised when a repository file cannot be indexed."""
