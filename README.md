# 🏗️ Gefährdungsbeurteilungs-MCP Server

MCP Server für automatisierte Gefährdungsbeurteilungen im Dachdecker- und Gerüstbaugewerbe. Analysiert Baustellenfotos/-videos und erstellt professionelle PDF-Dokumente nach BG BAU Muster.

## Architektur

```
┌──────────────────────────────────────────────────────┐
│  Coolify Predefined Network                          │
│                                                      │
│  ┌─────────────┐      ┌──────────────────────┐       │
│  │ dach-webui   │──────│ dach-mcp             │       │
│  │ (OpenWebUI)  │ HTTP │ (FastMCP Server)     │       │
│  │ Port 8080    │──────│ Port 32400            │       │
│  │              │      │                      │       │
│  │ Domain: ✅   │      │ Domain: ❌ (intern)  │       │
│  └──────┬───────┘      │                      │       │
│         │              │ Tools:               │       │
│         │              │ • video_to_frames    │       │
│         │              │ • extract_image_meta │       │
│         │              │ • create_gefaehrdung │       │
│         │              │ • get_standard_gef.  │       │
│         │              └──────────────────────┘       │
│         │                                            │
│         │  Azure AI Foundry (extern)                 │
│         └──────────────── GPT-4o / Claude ───────────│
└──────────────────────────────────────────────────────┘
```

**Verbindung**: OpenWebUI → `http://dach-mcp:32400/mcp` (Streamable HTTP MCP)

## Tools

| Tool | Beschreibung |
|------|-------------|
| `video_to_frames` | Extrahiert Keyframes aus Baustellenvideos (ffmpeg) |
| `extract_image_metadata` | GPS-Koordinaten & EXIF aus Baustellenfotos |
| `create_gefaehrdungsbeurteilung` | Generiert PDF mit Risikobewertung & Maßnahmen |
| `get_standard_gefaehrdungen` | Branchenübliche Standard-Gefährdungen (DGUV/BG BAU) |

## Handbuch (Wiki)

Installation, Deployment in Coolify, Einrichtung von OpenWebUI, Prüfen, Fehlerbehebung und Wartung stehen im [Wiki](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki):

- [Kurzanleitung Coolify Deployment](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki/Kurzanleitung)
- [MCP Server in Coolify deployen](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki/MCP-Server-Deployen)
- [OpenWebUI deployen](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki/OpenWebUI-Deployen) und [einrichten](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki/OpenWebUI-Einrichten) (inkl. Knowledge Base)
- [Prüfen und Fehlerbehebung](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki/Pruefen-und-Fehlerbehebung)
- [Updates und Wartung](https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server/wiki/Updates-und-Wartung)

## Lokale Entwicklung

```bash
# Repository klonen
git clone https://git.gm-itsolutions.de/gm-itsolutions/dach-mcp-server.git
cd dach-mcp-server

# Dependencies installieren
pip install -e .

# Server starten
python -m src.server

# → Läuft auf http://localhost:32400/mcp
```

### Testen mit MCP Inspector

```bash
npx @modelcontextprotocol/inspector http://localhost:32400/mcp
```

## Projektstruktur

```
dach-mcp-server/
├── Dockerfile
├── docker-compose.yml          # Coolify: MCP Server
├── pyproject.toml
├── .env.example
├── openwebui-system-prompt.md  # Copy-paste in OpenWebUI
├── coolify/
│   └── dach-webui-docker-compose.yml  # Coolify: OpenWebUI
├── src/
│   ├── server.py               # FastMCP Entry Point
│   └── tools/
│       ├── media.py            # Video/Bild-Verarbeitung
│       └── documents.py        # PDF-Generierung
└── templates/
    └── gefaehrdungsbeurteilung.json  # Standard-Schema
```
