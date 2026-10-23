# Copyright 2026 TRACE contributors
"""Environment settings independent of the sibling legacy agent."""

from typing import ClassVar

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read process environment; the CLI loads the chosen dotenv file."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(frozen=True, extra="ignore")
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    business_mcp_url: str = "http://localhost:8002/mcp"
    rag_mcp_url: str = "http://localhost:8003/mcp"
    physics_mcp_url: str = "http://localhost:8004/mcp"
    keycloak_issuer: str = ""
    keycloak_url: str = ""
    keycloak_realm: str = "trace"
    keycloak_audience: str = "trace-api"
    keycloak_jwks_url: str = ""
    internal_api_key: SecretStr = SecretStr("")

    @property
    def issuer(self) -> str:
        """Accept either an exact issuer or the existing URL plus realm settings."""
        if self.keycloak_issuer:
            return self.keycloak_issuer
        if self.keycloak_url:
            return f"{self.keycloak_url.rstrip('/')}/realms/{self.keycloak_realm}"
        return ""
