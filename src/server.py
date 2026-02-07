"""
Gefährdungsbeurteilungs-MCP Server
===================================
Stellt Tools für Baustellenanalyse und Dokumenterstellung bereit.

Transport: Streamable HTTP (direkt von OpenWebUI ansprechbar)
Endpoint:  http://<host>:32400/mcp
"""

import os
from mcp.server.fastmcp import FastMCP

from src.tools.media import register_media_tools
from src.tools.documents import register_document_tools

PORT = int(os.getenv("MCP_PORT", "32400"))
HOST = os.getenv("MCP_HOST", "0.0.0.0")

mcp = FastMCP(
    name="Gefährdungsbeurteilung",
    host=HOST,
    port=PORT,
    stateless_http=True,   # Kein Session-State → skalierbar & restart-sicher
    json_response=True,    # JSON statt SSE-Streaming → robuster für OpenWebUI
)

# Tools registrieren
register_media_tools(mcp)
register_document_tools(mcp)


def main():
    """Startet den MCP Server mit Streamable HTTP Transport."""
    print(f"🏗️  Gefährdungsbeurteilungs-MCP Server")
    print(f"📡  Streamable HTTP auf {HOST}:{PORT}/mcp")
    print(f"🔧  Tools: video_to_frames, extract_image_metadata, create_gefaehrdungsbeurteilung")

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
