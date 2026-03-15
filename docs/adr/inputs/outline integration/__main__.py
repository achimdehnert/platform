"""Entry point: python -m outline_mcp → starts the MCP server via stdio."""

import logging

from .server import mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
