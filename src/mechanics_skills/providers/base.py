"""
Base class for academic literature and metadata providers.
"""

import abc
import re
from typing import Any, List, Optional

from mechanics_skills.config import DEFAULT_EMAIL, settings
from mechanics_skills.http import HTTPClient, default_client
from mechanics_skills.models import PaperRecord


def clean_text(text: Any) -> str:
    """Normalize and clean whitespace from text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


class BaseProvider(abc.ABC):
    """Abstract base class for all academic providers."""

    name: str = "base"

    def __init__(
        self,
        client: Optional[HTTPClient] = None,
        email: Optional[str] = None,
    ):
        self.client = client or default_client
        self.email = email or settings.email or DEFAULT_EMAIL

    @abc.abstractmethod
    def search(self, query: str, limit: int = 15) -> List[PaperRecord]:
        """Search papers matching a query string."""
        pass

