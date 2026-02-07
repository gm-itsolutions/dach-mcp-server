"""
Gefährdungsbeurteilungs-MCP Server
===================================
Stellt Tools für Baustellenanalyse und Dokumenterstellung bereit.

Transport: Streamable HTTP (direkt von OpenWebUI ansprechbar)
Endpoint:  http://<host>:8001/mcp
"""

import os
from mcp.server.fastmcp import FastMCP

from src.tools.media import register_media_tools
from src.tools.documents import register_document_tools

mcp = FastMCP(
    name="Gefährdungsbeurteilung",
    stateless_http=True,   # Kein Session-State → skalierbar & restart-sicher
    json_response=True,    # JSON statt SSE-Streaming → robuster für OpenWebUI
)

# Tools registrieren
register_media_tools(mcp)
register_document_tools(mcp)


def main():
    """Startet den MCP Server mit Streamable HTTP Transport."""
    port = int(os.getenv("MCP_PORT", "8001"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    print(f"🏗️  Gefährdungsbeurteilungs-MCP Server")
    print(f"📡  Streamable HTTP auf {host}:{port}/mcp")
    print(f"🔧  Tools: video_to_frames, extract_image_metadata, create_gefaehrdungsbeurteilung")

    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()
