"""Domain-specific exception hierarchy for the STEM RADAR platform."""


class StemRadarException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(StemRadarException):
    """Raised when environment variables or configurations are invalid or missing."""

    pass


class AuthenticationError(StemRadarException):
    """Raised when an unauthorized user attempts an operation."""

    pass


class SourceCollectionError(StemRadarException):
    """Raised when an error occurs during feed or API collection."""

    def __init__(self, source_slug: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message, {"source_slug": source_slug, "status_code": status_code})
        self.source_slug = source_slug
        self.status_code = status_code


class FeedParsingError(SourceCollectionError):
    """Raised when RSS/Atom feed content cannot be parsed."""

    pass


class RateLimitExceededError(SourceCollectionError):
    """Raised when an external API rate limit is reached."""

    pass


class EntityNotFoundError(StemRadarException):
    """Raised when a requested resource (article, source, category) is not found."""

    pass


class DuplicateEntityError(StemRadarException):
    """Raised when an attempt to create a duplicate unique entity occurs."""

    pass


class AIServiceError(StemRadarException):
    """Raised when an error occurs during AI processing or LLM generation."""

    pass
