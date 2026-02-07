# Deployment-Anleitung: Sicherheitsberater MCP Server

## Komplettanleitung für GitHub Upload, Coolify Deployment & OpenWebUI Einrichtung

---

## Übersicht

Diese Anleitung beschreibt Schritt für Schritt:

1. **GitHub**: Repository erstellen und Code hochladen
2. **Coolify**: MCP Server deployen (Container 1)
3. **Coolify**: OpenWebUI deployen (Container 2)
4. **OpenWebUI**: MCP verbinden, Assistent einrichten, Knowledge Base befüllen

**Voraussetzungen:**
- GitHub Account (kostenlos oder Organisation)
- Coolify-Instanz mit Zugriff auf GitHub
- Azure AI Foundry Endpoint (GPT-4o)
- Domain für OpenWebUI (z.B. `ai.kundenname.de`)

---

## Teil 1: GitHub Repository erstellen & Code hochladen

### 1.1 Repository auf GitHub erstellen

1. Gehe zu [github.com/new](https://github.com/new)
2. Einstellungen:
   - **Repository name**: `dach-mcp-server`
   - **Visibility**: `Private` (empfohlen für Kundenprojekte)
   - **Initialize**: KEIN README, KEIN .gitignore (kommt aus dem Projekt)
3. **"Create repository"** klicken
4. Die angezeigte Repository-URL kopieren (z.B. `https://github.com/DEIN-ORG/dach-mcp-server.git`)

### 1.2 Lokales Git-Repository initialisieren und pushen

Öffne ein Terminal auf deinem Rechner und navigiere zum entpackten Projektordner:

```bash
# In den Projektordner wechseln
cd dach-mcp-server

# Git initialisieren
git init

# Alle Dateien zum Staging hinzufügen
git add .

# Prüfen was committet wird (optional, aber empfohlen)
git status
```

**Erwartete Ausgabe von `git status`:**
```
Changes to be committed:
  new file:   .dockerignore
  new file:   .env.example
  new file:   .gitignore
  new file:   Dockerfile
  new file:   README.md
  new file:   coolify/dach-webui-docker-compose.yml
  new file:   docker-compose.yml
  new file:   openwebui-system-prompt.md
  new file:   pyproject.toml
  new file:   src/__init__.py
  new file:   src/server.py
  new file:   src/tools/__init__.py
  new file:   src/tools/documents.py
  new file:   src/tools/media.py
  new file:   templates/gefaehrdungsbeurteilung.json
```

Wenn alles passt, committen und pushen:

```bash
# Ersten Commit erstellen
git commit -m "feat: Gefährdungsbeurteilungs-MCP Server – Initial Release

- FastMCP Server mit Streamable HTTP Transport
- Tools: video_to_frames, extract_image_metadata, create_gefaehrdungsbeurteilung, get_standard_gefaehrdungen
- Dockerfile mit ffmpeg für Video-Verarbeitung
- Coolify Docker Compose Konfigurationen
- OpenWebUI System-Prompt für Sicherheitsberater-Assistent
- Standard-Gefährdungen nach DGUV/BG BAU"

# Branch auf 'main' setzen (falls noch 'master')
git branch -M main

# Remote Repository verknüpfen
# ⚠️ URL mit deiner Organisation/Username ersetzen!
git remote add origin https://github.com/DEIN-ORG/dach-mcp-server.git

# Code hochladen
git push -u origin main
```

### 1.3 Authentifizierung bei GitHub

Falls GitHub nach Zugangsdaten fragt:

**Option A – HTTPS mit Personal Access Token (empfohlen):**

1. GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens
2. **"Generate new token"**:
   - Name: `coolify-deploy`
   - Expiration: 90 Tage
   - Repository access: "Only select repositories" → `dach-mcp-server`
   - Permissions → Repository permissions:
     - Contents: Read and write
     - Metadata: Read-only
3. Token kopieren
4. Beim `git push` als Passwort verwenden (Username = dein GitHub Username)

**Option B – SSH Key:**

```bash
# SSH Key generieren (falls noch keiner existiert)
ssh-keygen -t ed25519 -C "dein@email.de"

# Public Key anzeigen und kopieren
cat ~/.ssh/id_ed25519.pub

# In GitHub einfügen: Settings → SSH and GPG Keys → New SSH key

# Remote URL auf SSH ändern
git remote set-url origin git@github.com:DEIN-ORG/dach-mcp-server.git

# Nochmal pushen
git push -u origin main
```

### 1.4 Push verifizieren

Nach dem Push prüfen:
- Gehe zu `https://github.com/DEIN-ORG/dach-mcp-server`
- Alle 15 Dateien sollten sichtbar sein
- README.md wird automatisch als Startseite angezeigt

---

## Teil 2: MCP Server in Coolify deployen

### 2.1 GitHub in Coolify verbinden (falls noch nicht geschehen)

1. Coolify → **Settings** → **Git Sources**
2. **"+ Add"** → GitHub App
3. Der GitHub App diese Berechtigungen geben:
   - Repository access: "Only select repositories" → `dach-mcp-server` auswählen
   - Permissions: Contents (Read), Metadata (Read)
4. **"Install & Authorize"**

### 2.2 Neue Resource für MCP Server erstellen

1. Coolify → **Projects** → Projekt auswählen (oder neues erstellen, z.B. "Dachdecker KI")
2. **"+ New"** → **Docker Compose**
3. Konfiguration:
   - **Name**: `dach-mcp`
   - **Git Repository**: `DEIN-ORG/dach-mcp-server`
   - **Branch**: `main`
   - **Build Pack**: Docker Compose
   - **Docker Compose Location**: `docker-compose.yml` (Standard)

### 2.3 Netzwerk-Einstellungen (KRITISCH)

In den Resource-Settings:

1. → **Advanced** → **Network**
2. **"Connect to Predefined Network"**: ✅ **AKTIVIEREN**
3. **Domain**: ❌ **LEER LASSEN** (Server ist nur intern erreichbar)

> **Warum?** Durch das Predefined Network wird der Service-Name `dach-mcp` als DNS-Alias im `coolify`-Netzwerk registriert. OpenWebUI kann den Server dann über `http://dach-mcp:32400/mcp` erreichen.

### 2.4 Umgebungsvariablen setzen

Unter **Environment Variables**:

```
MCP_HOST=0.0.0.0
MCP_PORT=32400
TEMPLATES_DIR=/app/templates
TEMP_DIR=/tmp/processing
```

### 2.5 Deployment starten

1. **"Deploy"** klicken
2. Build-Log beobachten – sollte durchlaufen mit:
   - `Step: Installing ffmpeg` ✅
   - `Step: pip install` ✅
   - `Step: EXPOSE 32400` ✅
3. Warten bis Status **"Running"** zeigt
4. Healthcheck: Grüner Punkt (kann bis zu 30 Sekunden dauern)

### 2.6 Auto-Deploy aktivieren (optional)

Unter **Webhooks**:
1. **Auto Deploy**: ✅ Aktivieren
2. Coolify generiert eine Webhook-URL
3. In GitHub: Repository → Settings → Webhooks → "Add webhook"
4. Payload URL: Die Coolify Webhook-URL einfügen
5. Content type: `application/json`
6. Events: "Just the push event"
7. **"Add webhook"**

→ Jeder `git push` auf `main` triggert jetzt automatisch ein Re-Deployment.

---

## Teil 3: OpenWebUI in Coolify deployen

### 3.1 Neue Resource für OpenWebUI erstellen

1. Coolify → Gleiches Projekt → **"+ New"** → **Docker Compose**
2. Konfiguration:
   - **Name**: `dach-webui`
   - **Git Repository**: Gleiches Repo (`DEIN-ORG/dach-mcp-server`)
   - **Branch**: `main`
   - **Docker Compose Location**: `coolify/dach-webui-docker-compose.yml`

> **Hinweis:** Alternativ kannst du ein separates Repo für OpenWebUI erstellen. Für den Anfang ist es einfacher, alles in einem Repo zu halten.

### 3.2 Netzwerk & Domain

1. **"Connect to Predefined Network"**: ✅ **AKTIVIEREN**
2. **Domain**: `ai.kundenname.de` (deine Wunschdomain eingeben)
3. HTTPS: Automatisch via Let's Encrypt (Coolify Standard)

### 3.3 Umgebungsvariablen anpassen

Die folgenden Variablen müssen mit echten Werten befüllt werden:

```
# ── Basis ──
WEBUI_NAME=Sicherheitsberater
WEBUI_URL=https://ai.kundenname.de
ENABLE_SIGNUP=false
DEFAULT_USER_ROLE=user

# ── Azure AI Foundry ──
# ⚠️ ANPASSEN: Dein Azure OpenAI Endpoint
OPENAI_API_BASE_URL=https://DEIN-ENDPOINT.openai.azure.com/openai/deployments/gpt-4o/
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# ── RAG ──
RAG_EMBEDDING_MODEL=text-embedding-3-small
CHUNK_SIZE=1500
CHUNK_OVERLAP=200
RAG_TOP_K=8
```

### 3.4 Deployment starten

1. **"Deploy"** klicken
2. Warten bis Status **"Running"**
3. Domain aufrufen: `https://ai.kundenname.de`
4. **Erster Login**: Admin-Account erstellen (der erste User wird automatisch Admin)

---

## Teil 4: OpenWebUI einrichten

### 4.1 MCP Server verbinden

1. Einloggen als Admin
2. **Admin Panel** (Zahnrad oben rechts) → **Settings** → **Tools**
3. **"+"** (neues Tool hinzufügen)
4. Konfiguration:
   - **Typ**: `MCP (Streamable HTTP)`
   - **URL**: `http://dach-mcp:32400/mcp`
   - **Auth**: Keine / None
5. **"Save"**
6. Prüfen: Die 4 Tools sollten automatisch erkannt werden:
   - ✅ `video_to_frames`
   - ✅ `extract_image_metadata`
   - ✅ `create_gefaehrdungsbeurteilung`
   - ✅ `get_standard_gefaehrdungen`

> **Falls die Tools nicht erscheinen**: Prüfe ob der MCP Container läuft und die Netzwerkverbindung funktioniert (siehe Debugging in Teil 5).

### 4.2 Sicherheitsberater-Assistent anlegen

1. **Workspace** → **Models** → **"+ New Model"**
2. Konfiguration:
   - **Name**: `Sicherheitsberater`
   - **Model ID**: `sicherheitsberater` (wird automatisch generiert)
   - **Base Model**: GPT-4o (Azure)
   - **Description**: "KI-Assistent für Gefährdungsbeurteilungen im Dachdecker- und Gerüstbaugewerbe"
3. **System Prompt**: Den kompletten Inhalt aus `openwebui-system-prompt.md` einfügen
4. **Tools**: Alle 4 MCP Tools aktivieren (Häkchen setzen)
5. **Knowledge**: Siehe nächsten Schritt
6. **"Save"**

### 4.3 Knowledge Base (RAG) befüllen

1. **Workspace** → **Knowledge** → **"+ New Collection"**
2. Name: `Arbeitssicherheit Dachdecker & Gerüstbau`
3. Folgende Dokumente hochladen (als PDF):

| Dokument | Quelle |
|----------|--------|
| DGUV Vorschrift 38 – Bauarbeiten | dguv.de |
| TRBS 2121 – Gefährdung durch Absturz | baua.de |
| TRBS 2121 Teil 1 – Gerüste | baua.de |
| BG BAU Gefährdungsbeurteilung (Muster) | bgbau.de |
| ArbStättV (Arbeitsstättenverordnung) | gesetze-im-internet.de |
| BetrSichV (Betriebssicherheitsverordnung) | gesetze-im-internet.de |
| DGUV Information 201-023 (Dachdecker) | dguv.de |
| Firmeninterne Sicherheitsstandards | Kunde |

4. Nach Upload: Zurück zum **Sicherheitsberater**-Modell
5. **Knowledge** → Die erstellte Collection auswählen
6. **"Save"**

### 4.4 Benutzer anlegen

1. **Admin Panel** → **Users**
2. **"+ New User"** für jeden Mitarbeiter
3. Empfohlene Rollen:
   - **Bauleiter / SiFa**: `admin` (kann Modelle anpassen)
   - **Mitarbeiter**: `user` (kann nur chatten)

---

## Teil 5: Verifizierung & Debugging

### 5.1 Schnelltest

1. Im OpenWebUI Chat den **Sicherheitsberater** auswählen
2. Testen:
   ```
   Welche Standard-Gefährdungen gibt es bei Dacharbeiten?
   ```
   → Sollte `get_standard_gefaehrdungen` Tool aufrufen und eine Liste zurückgeben

3. Dann:
   ```
   Erstelle mir bitte eine Gefährdungsbeurteilung für eine 
   Dachsanierung in der Musterstraße 1, Berlin. 
   Ersteller ist Max Mustermann.
   ```
   → Sollte `create_gefaehrdungsbeurteilung` aufrufen und ein PDF generieren

### 5.2 Debugging-Befehle

Per SSH auf dem Coolify-Server:

```bash
# ── Netzwerk prüfen ──

# Alle Container im Coolify-Netzwerk anzeigen
docker network inspect coolify \
  --format '{{range .Containers}}{{.Name}} → {{.IPv4Address}}{{"\n"}}{{end}}'

# DNS-Auflösung: Kann OpenWebUI den MCP Server finden?
docker exec $(docker ps -qf "name=dach-webui") \
  sh -c "nslookup dach-mcp"

# HTTP-Verbindung: Ist der MCP Endpoint erreichbar?
docker exec $(docker ps -qf "name=dach-webui") \
  sh -c "curl -s http://dach-mcp:32400/mcp"

# Netzwerk-Aliase des MCP Containers prüfen
docker inspect $(docker ps -qf "name=dach-mcp") \
  --format '{{range $net, $config := .NetworkSettings.Networks}}{{$net}}: {{$config.Aliases}}{{"\n"}}{{end}}'

# ── Logs prüfen ──

# MCP Server Logs (letzte 50 Zeilen, live)
docker logs $(docker ps -qf "name=dach-mcp") --tail 50 -f

# OpenWebUI Logs
docker logs $(docker ps -qf "name=dach-webui") --tail 50 -f

# ── Container Status ──

# Beide Container laufen?
docker ps --filter "name=dach-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 5.3 Häufige Probleme

| Problem | Ursache | Lösung |
|---------|---------|--------|
| "Tool konnte nicht ausgeführt werden" | MCP Container nicht erreichbar | Prüfe: Predefined Network aktiviert? DNS `nslookup dach-mcp` funktioniert? |
| Tools werden nicht in OpenWebUI angezeigt | Falsche URL oder Transport-Typ | URL muss `http://dach-mcp:32400/mcp` sein (nicht https, nicht /sse) |
| PDF-Erstellung schlägt fehl | ffmpeg fehlt im Container | Dockerfile prüfen: `apt-get install ffmpeg` vorhanden? |
| "Modell nicht erreichbar" | Azure API Key falsch | Umgebungsvariable `OPENAI_API_KEY` in dach-webui prüfen |
| Container startet, fällt aber sofort | Port-Konflikt oder Crash | `docker logs` prüfen, ggf. Port 32400 belegt |
| OpenWebUI zeigt keine Domain | DNS noch nicht propagiert | DNS-Eintrag prüfen: A-Record auf Coolify-Server-IP? |

---

## Teil 6: Updates & Wartung

### Code-Updates einspielen

```bash
# Lokale Änderungen committen
cd dach-mcp-server
git add .
git commit -m "fix: Beschreibung der Änderung"
git push origin main

# Falls Auto-Deploy aktiv: Coolify baut automatisch neu
# Falls nicht: In Coolify manuell "Redeploy" klicken
```

### OpenWebUI Version aktualisieren

In Coolify unter `dach-webui`:
1. Image-Tag prüfen: `ghcr.io/open-webui/open-webui:main` (latest)
2. **"Redeploy"** klicken → zieht automatisch das neueste Image

### Backup

```bash
# OpenWebUI Daten (Chats, Knowledge Base, User-Einstellungen)
docker cp $(docker ps -qf "name=dach-webui"):/app/backend/data ./backup-$(date +%Y%m%d)/
```

---

## Zusammenfassung: Deployment-Reihenfolge

```
1. GitHub Repo erstellen & Code pushen
      ↓
2. Coolify: dach-mcp deployen
   - Docker Compose
   - Predefined Network: ✅
   - Domain: keine
   - Warten auf "Running" + grüner Healthcheck
      ↓
3. Coolify: dach-webui deployen
   - Docker Compose
   - Predefined Network: ✅
   - Domain: ai.kundenname.de
   - Azure API Key setzen
      ↓
4. OpenWebUI: MCP verbinden
   - Typ: Streamable HTTP
   - URL: http://dach-mcp:32400/mcp
      ↓
5. OpenWebUI: Assistent einrichten
   - System-Prompt einfügen
   - Tools aktivieren
   - Knowledge Base hochladen
      ↓
6. Testen & Benutzer anlegen
```
