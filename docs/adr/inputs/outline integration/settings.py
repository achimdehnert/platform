"""Settings for outline_mcp — pydantic-settings, env-basiert (ADR-045 compliant)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class OutlineMCPSettings(BaseSettings):
    """All configuration from environment variables.

    Required in .env / .windsurf/mcp.json env:
        OUTLINE_URL            — Base URL of the Outline instance (e.g. https://knowledge.iil.pet)
        OUTLINE_API_TOKEN      — Personal API token (read+write access)

    Optional:
        OUTLINE_TIMEOUT        — HTTP request timeout in seconds (default: 30)
        OUTLINE_RETRY_ATTEMPTS — Number of retry attempts on transient errors (default: 3)
        OUTLINE_COLLECTION_RUNBOOKS    — Collection ID for Runbooks
        OUTLINE_COLLECTION_CONCEPTS    — Collection ID for Architektur-Konzepte
        OUTLINE_COLLECTION_LESSONS     — Collection ID for Lessons Learned
        OUTLINE_COLLECTION_ADR_DRAFTS  — Collection ID for ADR-Drafts
        OUTLINE_COLLECTION_ADR_MIRROR  — Collection ID for ADRs (Read-Only Mirror)
        OUTLINE_COLLECTION_HUB_DOCS    — Collection ID for Hub-Dokumentation
    """

    model_config = SettingsConfigDict(
        env_prefix="OUTLINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str
    api_token: str
    timeout: float = 30.0
    retry_attempts: int = 3

    # Collection IDs — populated after Outline setup (Phase 5.1)
    # Empty string means "search all collections"
    collection_runbooks: str = ""
    collection_concepts: str = ""
    collection_lessons: str = ""
    collection_adr_drafts: str = ""
    collection_adr_mirror: str = ""
    collection_hub_docs: str = ""

    @property
    def base_url(self) -> str:
        """Normalized base URL without trailing slash."""
        return self.url.rstrip("/")


def get_settings() -> OutlineMCPSettings:
    """Return settings instance. Cached at module level after first call."""
    return OutlineMCPSettings()  # type: ignore[call-arg]
