"""
Custom exception classes for the application.

Each layer has its own exception type for clear error attribution
in logs and API responses.
"""


class NewsBotError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(self.message)


class IngestionError(NewsBotError):
    """Raised when a data ingestion operation fails."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"Ingestion error [{source}]: {message}")


class ProcessingError(NewsBotError):
    """Raised when article processing fails (classification, embedding, etc.)."""

    def __init__(self, step: str, message: str):
        self.step = step
        super().__init__(f"Processing error [{step}]: {message}")


class RAGError(NewsBotError):
    """Raised when the RAG pipeline encounters an error."""

    def __init__(self, node: str, message: str):
        self.node = node
        super().__init__(f"RAG error [{node}]: {message}")


class ExternalAPIError(NewsBotError):
    """Raised when an external API call fails."""

    def __init__(self, api_name: str, status_code: int | None, message: str):
        self.api_name = api_name
        self.status_code = status_code
        super().__init__(
            f"External API error [{api_name}] (status={status_code}): {message}"
        )
