"""
Configuration module for mechanics-agent-skills.
"""

import os
from dataclasses import dataclass

DEFAULT_EMAIL = os.environ.get("MECHANICS_EMAIL", "")
DEFAULT_TIMEOUT = float(os.environ.get("MECHANICS_TIMEOUT", "30.0"))
DEFAULT_MAX_RETRIES = int(os.environ.get("MECHANICS_RETRIES", "3"))
DEFAULT_USER_AGENT = os.environ.get(
    "MECHANICS_USER_AGENT",
    f"MechanicsAgentSkills/3.1.0" + (f" (mailto:{DEFAULT_EMAIL})" if DEFAULT_EMAIL else "")
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
        email_val = os.environ.get("MECHANICS_EMAIL", DEFAULT_EMAIL)
        ua_val = os.environ.get(
            "MECHANICS_USER_AGENT",
            f"MechanicsAgentSkills/3.1.0" + (f" (mailto:{email_val})" if email_val else "")
        )
        return cls(
            email=email_val,
            timeout=float(os.environ.get("MECHANICS_TIMEOUT", str(DEFAULT_TIMEOUT))),
            max_retries=int(os.environ.get("MECHANICS_RETRIES", str(DEFAULT_MAX_RETRIES))),
            user_agent=ua_val,
            http_backend=os.environ.get("MECHANICS_HTTP_BACKEND", "auto"),
        )


settings = Settings.from_env()
