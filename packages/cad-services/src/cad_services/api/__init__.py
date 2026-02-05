"""
CAD-Hub FastAPI Application
ADR-009: API Layer with Pydantic schemas, database-driven
"""

from cad_services.api.app import app, create_app


__all__ = ["app", "create_app"]
