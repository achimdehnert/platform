"""MCP Server Integration für BFA Agent."""

from agents.mcp import MCPServerStdio, MCPServerSse
from pathlib import Path
import os


def create_bfa_mcp_server(server_path: str | Path | None = None) -> MCPServerStdio:
    """Erstellt MCP Server für BFA CAD Tools.
    
    Args:
        server_path: Pfad zum MCP Server Skript (optional)
        
    Returns:
        Konfigurierter MCPServerStdio
    """
    if server_path is None:
        server_path = Path(__file__).parent / "mcp_server" / "server.py"
    
    return MCPServerStdio(
        name="bfa-cad-mcp",
        command="python",
        args=[str(server_path)],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).parent.parent)
        }
    )


def create_external_mcp_server(
    command: str,
    args: list[str],
    name: str = "external-mcp"
) -> MCPServerStdio:
    """Bindet einen externen MCP Server ein."""
    return MCPServerStdio(
        name=name,
        command=command,
        args=args
    )


def create_sse_mcp_server(url: str, name: str = "sse-mcp") -> MCPServerSse:
    """Verbindet zu einem SSE MCP Server (HTTP)."""
    return MCPServerSse(
        name=name,
        url=url
    )


class MCPServers:
    """Factory für häufig verwendete MCP Server."""
    
    # ========================================
    # BFA-spezifische Server
    # ========================================
    
    @staticmethod
    def bfa_cad(server_script: str | None = None) -> MCPServerStdio:
        """BFA CAD MCP Server für Ex-Schutz Analyse."""
        return create_bfa_mcp_server(server_script)
    
    # ========================================
    # Research & Akademische Quellen
    # ========================================
    
    @staticmethod
    def paper_search() -> MCPServerStdio:
        """Academic Paper Search MCP.
        
        Sucht und lädt Papers von:
        - arXiv (Physik, Engineering, CS)
        - PubMed (Biomedizin, Toxikologie)
        - bioRxiv/medRxiv (Preprints)
        - Semantic Scholar (Breit)
        - Google Scholar
        - IACR ePrint (Kryptographie)
        
        Installation:
            pip install paper-search-mcp
            # oder
            uvx paper-search-mcp
        """
        return MCPServerStdio(
            name="paper-search",
            command="uvx",
            args=["paper-search-mcp"]
        )
    
    @staticmethod
    def paper_search_pip() -> MCPServerStdio:
        """Paper Search via pip-installiertes Package."""
        return MCPServerStdio(
            name="paper-search",
            command="python",
            args=["-m", "paper_search_mcp.server"]
        )
    
    # ========================================
    # Utility Server
    # ========================================
    
    @staticmethod
    def filesystem(allowed_paths: list[str]) -> MCPServerStdio:
        """MCP Filesystem Server."""
        return MCPServerStdio(
            name="filesystem",
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                *allowed_paths
            ]
        )
    
    @staticmethod
    def sqlite(db_path: str) -> MCPServerStdio:
        """MCP SQLite Server."""
        return MCPServerStdio(
            name="sqlite",
            command="uvx",
            args=["mcp-server-sqlite", "--db-path", db_path]
        )
    
    @staticmethod
    def fetch() -> MCPServerStdio:
        """MCP Fetch Server für Web-Requests."""
        return MCPServerStdio(
            name="fetch",
            command="uvx",
            args=["mcp-server-fetch"]
        )
    
    @staticmethod
    def memory(memory_path: str | None = None) -> MCPServerStdio:
        """MCP Memory Server für persistenten Kontext."""
        args = ["mcp-server-memory"]
        if memory_path:
            args.extend(["--memory-path", memory_path])
        return MCPServerStdio(
            name="memory",
            command="uvx",
            args=args
        )


# Convenience: Vorkonfigurierte Server-Kombinationen
class MCPServerSets:
    """Vorkonfigurierte Server-Sets für verschiedene Use Cases."""
    
    @staticmethod
    def bfa_full() -> list[MCPServerStdio]:
        """Vollständiges BFA Setup: CAD + Research."""
        return [
            MCPServers.bfa_cad(),
            MCPServers.paper_search(),
        ]
    
    @staticmethod
    def research_only() -> list[MCPServerStdio]:
        """Nur Research-Tools."""
        return [
            MCPServers.paper_search(),
            MCPServers.fetch(),
        ]
    
    @staticmethod
    def bfa_with_storage(db_path: str) -> list[MCPServerStdio]:
        """BFA mit Datenbank-Speicher."""
        return [
            MCPServers.bfa_cad(),
            MCPServers.sqlite(db_path),
        ]
