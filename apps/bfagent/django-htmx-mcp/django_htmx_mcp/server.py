"""
Django-HTMX MCP Server

Ein MCP Server der Tools für Django + HTMX Entwicklung bereitstellt:
- Model Generation
- View Generation (CBV, HTMX-optimiert)
- Template Generation
- Form Generation
- URL Routing
- Testing
- Scaffolding
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # MCP STDIO erfordert stderr für Logs
)
logger = logging.getLogger("django-htmx-mcp")

# MCP Server-Instanz - direkt erstellt für Tool-Registrierung
mcp = FastMCP(
    name="django-htmx-mcp",
    instructions="""
    Django-HTMX MCP Server für Code-Generierung.
    
    Verfügbare Tool-Kategorien:
    1. Models: generate_django_model, generate_choices_class, generate_model_manager
    2. Views: generate_cbv, generate_htmx_action_view, generate_htmx_search_view
    3. Templates: generate_htmx_list_template, generate_htmx_form_template, generate_htmx_component
    4. Forms: generate_model_form, generate_filter_form, generate_search_form
    5. URLs: generate_crud_urls, generate_urlpatterns, generate_htmx_action_urls
    6. Tests: generate_model_tests, generate_view_tests, generate_conftest
    7. Scaffolding: scaffold_django_app, scaffold_htmx_component
    8. Analysis: analyze_view_for_htmx, convert_fbv_to_cbv, analyze_template_for_htmx
    
    Alle Tools generieren produktionsreifen Code mit Best Practices.
    """
)


def main():
    """Entry point für den MCP Server."""
    logger.info("Starting Django-HTMX MCP Server...")
    
    # Import tools to register them with MCP (Decorators registrieren Tools)
    from django_htmx_mcp.tools import models  # noqa: F401
    from django_htmx_mcp.tools import views  # noqa: F401
    from django_htmx_mcp.tools import templates  # noqa: F401
    from django_htmx_mcp.tools import forms  # noqa: F401
    from django_htmx_mcp.tools import urls  # noqa: F401
    from django_htmx_mcp.tools import tests  # noqa: F401
    from django_htmx_mcp.tools import scaffolding  # noqa: F401
    from django_htmx_mcp.tools import analysis  # noqa: F401
    
    logger.info("All tools registered. Starting server...")
    mcp.run()


if __name__ == "__main__":
    main()
