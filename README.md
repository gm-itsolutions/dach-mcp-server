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

## Lokale Entwicklung

```bash
# Repository klonen
git clone https://github.com/DEIN-ORG/dach-mcp-server.git
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

## Coolify Deployment

### 1. MCP Server deployen

1. **Neue Resource** → Docker Compose → GitHub Repository verknüpfen
2. **Build Pack**: Docker Compose
3. **Connect to Predefined Network**: ✅ Aktivieren
4. **Domain**: Keine (nur intern)
5. Auto Deploy: ✅

### 2. OpenWebUI deployen

1. Separate Coolify Resource erstellen (siehe `coolify/dach-webui-docker-compose.yml`)
2. **Connect to Predefined Network**: ✅ Aktivieren
3. **Domain**: `ai.kundenname.de` vergeben
4. Umgebungsvariablen anpassen (Azure Endpoint, API Key)

### 3. MCP in OpenWebUI verbinden

```
Admin Panel → Settings → Tools → "+"
Typ:  MCP (Streamable HTTP)
URL:  http://dach-mcp:32400/mcp
```

### 4. Assistent einrichten

```
Workspace → Models → "+" New Model
Name:          Sicherheitsberater
Base Model:    GPT-4o (Azure)
System Prompt: [Inhalt von openwebui-system-prompt.md einfügen]
Tools:         ✅ Alle MCP Tools aktivieren
Knowledge:     DGUV/BG BAU Dokumente hochladen
```

## Knowledge Base (RAG)

Folgende Dokumente in OpenWebUI als Knowledge Base hochladen:

- DGUV Vorschrift 38 – Bauarbeiten
- TRBS 2121 – Absturzgefahr
- BG BAU Gefährdungsbeurteilungs-Muster
- ArbStättV / BetrSichV (relevante Auszüge)
- Firmeninterne Sicherheitsstandards

## Debugging

```bash
# DNS-Auflösung testen (von OpenWebUI aus)
docker exec $(docker ps -qf "name=dach-webui") sh -c "nslookup dach-mcp"

# MCP Server erreichbar?
docker exec $(docker ps -qf "name=dach-webui") sh -c "curl -s http://dach-mcp:32400/mcp"

# Netzwerk-Aliase prüfen
docker inspect $(docker ps -qf "name=dach-mcp") \
  --format '{{range $net, $config := .NetworkSettings.Networks}}{{$net}}: {{$config.Aliases}}{{"\n"}}{{end}}'

# MCP Server Logs
docker logs $(docker ps -qf "name=dach-mcp") --tail 50 -f
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
