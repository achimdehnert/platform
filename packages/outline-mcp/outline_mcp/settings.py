"""Configuration via pydantic-settings (env-based, ADR-045)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Outline MCP Server settings.

    All values are read from environment variables with prefix OUTLINE_MCP_.
    Example: OUTLINE_MCP_OUTLINE_URL=https://knowledge.iil.pet
    """

    outline_url: str = "https://knowledge.iil.pet"
    outline_api_token: str
    default_limit: int = 10

    # Collection IDs (knowledge.iil.pet)
    collection_runbooks: str = "a67c9777-3bc3-401a-9de3-91f0cc6c56d9"
    collection_concepts: str = "04064c28-a847-4bec-9bc3-a74d5e1012a2"
    collection_lessons: str = "db8291c2-f135-4834-878e-224db5673ab6"
    collection_adr_drafts: str = "21678f65-80d7-4594-a1d2-660c8770acfa"
    collection_hub_docs: str = "69d7d88b-7f15-447e-8da5-efc500f8bd29"
    collection_adr_mirror: str = "cf12fd43-4b14-4e1f-9603-dd7cb124071f"

    model_config = {"env_prefix": "OUTLINE_MCP_"}
