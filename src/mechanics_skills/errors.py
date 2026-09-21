"""
Exceptions hierarchy for mechanics-agent-skills.
"""

from typing import Any, Optional


class MechanicsError(Exception):
    """Base exception for all mechanics-agent-skills errors."""
    pass


class ProviderError(MechanicsError):
    """Exception raised when an upstream academic provider returns an error."""

    def __init__(
        self,
        message: str,
        provider: str = "",
        status_code: Optional[int] = None,
        details: Any = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        prefix = f"[{self.provider}] " if self.provider else ""
        code = f" (Status {self.status_code})" if self.status_code else ""
        return f"{prefix}{super().__str__()}{code}"


class RateLimitError(ProviderError):
    """Exception raised when an API rate limit or budget exhaustion occurs."""

    def __init__(
        self,
        message: str,
        provider: str = "",
        retry_after: Optional[float] = None,
        details: Any = None,
    ):
        super().__init__(message, provider=provider, status_code=429, details=details)
        self.retry_after = retry_after


class ParsingError(MechanicsError):
    """Exception raised when parsing responses (XML, JSON, HTML) fails."""
    pass


class HTTPError(MechanicsError):
    """Exception raised when an HTTP transport request fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        url: str = "",
        body: str = "",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.body = body

    def __str__(self) -> str:
        code = f" {self.status_code}" if self.status_code else ""
        url_part = f" for {self.url}" if self.url else ""
        return f"HTTP error{code}{url_part}: {super().__str__()}"


class MissingDependencyError(MechanicsError):
    """Exception raised when an optional package is required but missing."""

    def __init__(self, feature: str, package: str, install_hint: str):
        msg = f"Feature '{feature}' requires optional package '{package}'. Install via: {install_hint}"
        super().__init__(msg)
        self.feature = feature
        self.package = package
        self.install_hint = install_hint

