"""Settings for Deployment MCP Server."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for Deployment MCP Server."""

    model_config = SettingsConfigDict(
        env_prefix="DEPLOYMENT_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Hetzner Cloud API
    hetzner_api_token: SecretStr = Field(
        default=SecretStr(""),
        description="Hetzner Cloud API Token",
    )
    hetzner_api_url: str = Field(
        default="https://api.hetzner.cloud/v1",
        description="Hetzner Cloud API Base URL",
    )

    # SSH Configuration
    ssh_host: str = Field(
        default="",
        description="Default SSH host for remote operations",
    )
    ssh_port: int = Field(
        default=22,
        description="SSH port",
    )
    ssh_user: str = Field(
        default="root",
        description="SSH username",
    )
    ssh_key_path: str = Field(
        default="~/.ssh/id_rsa",
        description="Path to SSH private key",
    )
    ssh_timeout: int = Field(
        default=30,
        description="SSH connection timeout in seconds",
    )

    # PostgreSQL defaults
    postgres_default_port: int = Field(
        default=5432,
        description="Default PostgreSQL port",
    )
    postgres_default_user: str = Field(
        default="postgres",
        description="Default PostgreSQL user",
    )

    # Docker defaults
    docker_compose_path: str = Field(
        default="/opt/docker",
        description="Default path for docker-compose files",
    )

    # Server defaults for provisioning
    default_server_type: str = Field(
        default="cx22",
        description="Default Hetzner server type",
    )
    default_image: str = Field(
        default="ubuntu-24.04",
        description="Default OS image for new servers",
    )
    default_location: str = Field(
        default="fsn1",
        description="Default datacenter location",
    )

    # Safety settings
    require_confirmation: bool = Field(
        default=True,
        description="Require confirmation for destructive operations",
    )


# Global settings instance
settings = Settings()
