"""
Configuration module for mechanics-agent-skills.
"""

import os
from dataclasses import dataclass

DEFAULT_EMAIL = os.environ.get("MECHANICS_EMAIL", "academic_researcher@mechanics.edu")
DEFAULT_TIMEOUT = float(os.environ.get("MECHANICS_TIMEOUT", "30.0"))
DEFAULT_MAX_RETRIES = int(os.environ.get("MECHANICS_RETRIES", "3"))
DEFAULT_USER_AGENT = os.environ.get(
    "MECHANICS_USER_AGENT",
    f"Mozilla/5.0 (compatible; MechanicsSkills/3.0.0; +mailto:{DEFAULT_EMAIL})"
)

# Domain-specific rate limits (requests per second)
DEFAULT_RATE_LIMITS = {
    "api.openalex.org": 10.0,
    "api.crossref.org": 5.0,
    "export.arxiv.org": 0.33,  # Strict limit: max 1 request every 3 seconds per arXiv ToS
    "api.semanticscholar.org": 1.0,
    "api.unpaywall.org": 5.0,
}


@dataclass
class Settings:
    email: str = DEFAULT_EMAIL
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    user_agent: str = DEFAULT_USER_AGENT
    http_backend: str = os.environ.get("MECHANICS_HTTP_BACKEND", "auto")  # 'auto', 'urllib', 'httpx'

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            email=os.environ.get("MECHANICS_EMAIL", DEFAULT_EMAIL),
            timeout=float(os.environ.get("MECHANICS_TIMEOUT", str(DEFAULT_TIMEOUT))),
            max_retries=int(os.environ.get("MECHANICS_RETRIES", str(DEFAULT_MAX_RETRIES))),
            user_agent=os.environ.get("MECHANICS_USER_AGENT", DEFAULT_USER_AGENT),
            http_backend=os.environ.get("MECHANICS_HTTP_BACKEND", "auto"),
        )


settings = Settings.from_env()

