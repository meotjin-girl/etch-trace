"""TRACE backend lifespan, shared dependencies, and API composition."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import anyio
from agent_server_alerts import watch as watch_agent_server_alerts
from api_dependencies import Dependencies, Runtime
from dotenv import load_dotenv
from fastapi import FastAPI
from investigations_api import router as investigations_router
from investigations_store import InvestigationsStore
from legacy_api import router as legacy_router
from v1_alerts import watch as watch_alerts
from v1_auth import Authenticator
from v1_models import DEFAULT_SOP_DIR, Settings
from v1_store import Store


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime: Runtime | None = None

    def current() -> Runtime:
        assert runtime is not None, "Application lifespan has not started"
        return runtime

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        nonlocal runtime
        _ = load_dotenv(Path(__file__).parent.parent / ".env")
        config = settings or Settings(
            os.getenv("DATABASE_URL", "postgresql://trace:trace@localhost:5432/trace"),
            os.getenv("AGENT_URL", "http://agent:8001"),
            os.getenv("INTERNAL_API_KEY", "dev-internal-key"),
            os.getenv("SOP_DOCUMENTS_DIR", DEFAULT_SOP_DIR),
            keycloak_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080/auth"),
            keycloak_realm=os.getenv("KEYCLOAK_REALM", "trace"),
            keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID", "trace-web"),
            keycloak_audience=os.getenv("KEYCLOAK_AUDIENCE", "trace-api"),
            keycloak_jwks_url=os.getenv("KEYCLOAK_JWKS_URL", ""),
            prometheus_url=os.getenv("PROMETHEUS_URL", ""),
            agent_server_url=os.getenv("AGENT_SERVER_URL", ""),
        )
        if not config.internal_api_key:
            raise RuntimeError("INTERNAL_API_KEY must not be empty")
        store = Store(config.database_url)
        investigations = InvestigationsStore(store.pool)
        runtime = Runtime(store, config, Authenticator(config), investigations)
        application.state.settings = config
        application.state.store = store
        try:
            await anyio.to_thread.run_sync(store.initialize)
            await anyio.to_thread.run_sync(investigations.initialize)
            async with anyio.create_task_group() as background:
                if config.prometheus_url:
                    if config.agent_server_url:
                        _ = background.start_soon(watch_agent_server_alerts, config)
                    else:
                        _ = background.start_soon(watch_alerts, store, config)
                yield
                background.cancel_scope.cancel()
        finally:
            await anyio.to_thread.run_sync(store.pool.close)
            runtime = None

    app = FastAPI(title="TRACE Backend", version="1.0.0", lifespan=lifespan)
    dependencies = Dependencies(current)
    app.include_router(investigations_router(dependencies))
    app.include_router(legacy_router(dependencies, lambda: datetime.now(UTC).timestamp()))

    @app.get("/api/auth/config")
    def auth_config() -> dict[str, str]:
        config = current().settings
        return {
            "url": config.keycloak_url,
            "realm": config.keycloak_realm,
            "clientId": config.keycloak_client_id,
        }

    return app


app = create_app()
