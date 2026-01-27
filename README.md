[![CI Tests](https://github.com/t-neumann/GenomicOps-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/t-neumann/GenomicOps-MCP/actions/workflows/tests.yml)

# 🧬 GenomicOps-MCP

**GenomicOps-MCP** is a Model Context Protocol (MCP) server exposing genomic operations for AI-assisted bioinformatics workflows.
It provides tools for querying UCSC genome browser tracks, performing coordinate liftover between assemblies, and exploring available species and assemblies — all accessible in dual mode:

- 🧠 **Model Context Protocol (MCP)** — for integration with Claude Desktop and other AI clients.
- 🌐 **FastAPI REST API** — for human-readable, local testing and web interaction.

It currently provides tools to query **UCSC genome browser tracks**, including feature overlaps and assembly listings.

---

## 🚀 Features

* **Coordinate Liftover**: Convert genomic coordinates between assemblies (e.g., hg19 → hg38)
* **Feature Overlaps**: Query UCSC tracks for annotations overlapping a region
* **Species & Assembly Listing**: Explore all UCSC-supported organisms and genome builds
* **Track Discovery**: List available tracks for any assembly
* **Auto-provisioning**: Automatically downloads liftOver binary and chain files as needed

- **Dual Transport**: FastMCP powers both stdio (MCP) and streamable-http (web API) modes
- **MCP integration:** Claude Desktop and other MCP-compatible LLM clients can call tools like `get_overlapping_features`.
- **FastAPI web API:** Test and debug the same logic locally in a browser or via `curl`.
- **Unified backend:** One codebase (`server.py`) supports both modes.
- **FastMCP-powered:** Built with [FastMCP](https://gofastmcp.com) for standard-compliant and rapid MCP development.

---

## 📁 Project Structure

```
GenomicOps-MCP/
├── server.py                 # FastMCP + FastAPI entrypoint
├── genomicops/
│   ├── __init__.py
│   ├── liftover.py           # Coordinate liftover logic
│   └── ucsc_rest.py          # UCSC REST API client
├── tests/
│   ├── conftest.py           # Pytest configuration
│   ├── test_api.py
│   ├── test_liftover.py
│   ├── test_mcp.py
│   └── test_ucsc_rest.py
├── pyproject.toml
└── uv.lock
```

---

## 🧩 Installation

### 1️⃣ Prerequisites

- **Python ≥ 3.11**
- **uv** (recommended for managing virtual environments and dependencies)

Install uv globally (if not already):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2️⃣ Clone and enter the project

```bash
git clone https://github.com/YOUR_USERNAME/GenomicOps-MCP.git
cd GenomicOps-MCP
```

### 3️⃣ Install dependencies via `uv`

```bash
uv sync
```

This ensures your environment matches the locked versions in `uv.lock`.

---

## 🧬 Available Tools

| Tool | Description |
|------|-------------|
| `get_overlapping_features` | Query UCSC tracks for features overlapping a genomic region |
| `lift_over_coordinates` | Convert coordinates between genome assemblies |
| `list_species` | List all available species from UCSC |
| `list_assemblies` | Get all assemblies for a given species |
| `list_ucsc_tracks` | List available tracks for a genome assembly |

---

## 🧠 Running in MCP Mode

### stdio Transport (for Claude Desktop)

Run the server as an **MCP endpoint**:

```bash
uv run server.py
```

This launches the MCP server over **stdio**, ready for a client like Claude Desktop to connect.

You should see something like:

```
────────────────────────────────────────────────────────────────────────────╮
│                                                                            │
│        _ __ ___  _____           __  __  _____________    ____    ____     │
│       _ __ ___ .'____/___ ______/ /_/  |/  / ____/ __ \  |___ \  / __ \    │
│      _ __ ___ / /_  / __ `/ ___/ __/ /|_/ / /   / /_/ /  ___/ / / / / /    │
│     _ __ ___ / __/ / /_/ (__  ) /_/ /  / / /___/ ____/  /  __/_/ /_/ /     │
│    _ __ ___ /_/    \____/____/\__/_/  /_/\____/_/      /_____(*)____/      │
│                                                                            │
│                                                                            │
│                                FastMCP  2.0                                │
│                                                                            │
│                                                                            │
│                 🖥️  Server name:     ucsc-mcp                               │
│                 📦 Transport:       STDIO                                  │
│                                                                            │
│                 🏎️  FastMCP version: 2.12.4                                 │
│                 🤝 MCP SDK version: 1.16.0                                 │
│                                                                            │
│                 📚 Docs:            https://gofastmcp.com                  │
│                 🚀 Deploy:          https://fastmcp.cloud                  │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯


[10/08/25 13:26:00] INFO     Starting MCP server 'ucsc-mcp' with transport 'stdio'
```

### streamable-http Transport (for remote/web clients)

```bash
uv run fastmcp run server.py --transport streamable-http
```

Test with MCP Inspector:
```bash
npx @modelcontextprotocol/inspector --transport http --server-url http://localhost:8000/mcp
```

---

### 🧩 Add to Claude Desktop

To connect this MCP to Claude Desktop:

#### Option 1: Manual Configuration

Add this entry to your `claude_desktop_config.json` to run with default `STDIO` protocol:

```json
{
  "mcpServers": {
    "GenomicOps-MCP": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/GenomicOps-MCPP",
        "/path/to/GenomicOps-MCP/server.py"
      ]
    }
  }
}
```

Or install via FastMCP CLI:

```bash
fastmcp install claude-desktop server.py \
  --python 3.11 \
  --project /path/to/GenomicOps-MCP
```

---

### 🌐 Running in FastAPI Mode

For local testing with Swagger UI:

```bash
uv run server.py api
```

Open http://localhost:8000/docs for interactive API documentation.

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/overlaps` | Query overlapping genomic features |
| `POST` | `/liftover` | Convert coordinates between assemblies |
| `GET` | `/species` | List all UCSC species |
| `GET` | `/assemblies/{species}` | Get assemblies for a species |
| `GET` | `/tracks/{genome}` | List tracks for an assembly |
| `POST` | `/refresh-cache` | Force-refresh UCSC genome cache |

### Example Requests

```bash
# Get features overlapping MYC locus
curl -X POST http://localhost:8000/overlaps \
  -H "Content-Type: application/json" \
  -d '{"region": "chr8:127735433-127740477", "genome": "hg38", "track": "knownGene"}'

# Liftover coordinates from hg19 to hg38
curl -X POST http://localhost:8000/liftover \
  -H "Content-Type: application/json" \
  -d '{"region": "chr1:1000000-1001000", "from_asm": "hg19", "to_asm": "hg38"}'

# List human assemblies
curl http://localhost:8000/assemblies/Homo%20sapiens
```

---

## 🐳 Docker Deployment

### Build

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t tobneu/genomicops:latest --push .
```

### Run Locally

```bash
docker run -d -p 8000:8000 --name genomicops tobneu/genomicops:latest
```

### :cloud: AWS EC2 Deployment

1. **Launch EC2 instance** (Amazon Linux 2023 AMI, t3.small is sufficient)

   Configure security group:
   - SSH (port 22) from your IP
   - Custom TCP (port 8000) from your IP

2. **Install Docker**

   ```bash
   sudo yum update -y
   sudo yum install docker -y
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -a -G docker ec2-user
   exit  # Log out and back in
   ```

3. **Run container**

   ```bash
   docker run -d -p 8000:8000 --name genomicops --restart unless-stopped tobneu/genomicops:latest
   ```

4. **Verify**

   ```bash
   npx @modelcontextprotocol/inspector --transport streamable-http --server-url http://l<EC2-IP>:8000/mcp
   ```  
---

## 🧪 Testing

```bash
# Run unit tests
uv run pytest

# Run smoke tests (quick API validation)
uv run pytest --smoke

# Run integration tests (real UCSC API calls)
uv run pytest --integration

# Run all tests with coverage
uv run pytest --cov=genomicops --cov-report=html
```

---

## ⚠️ Limitations

* **UCSC API Dependency**: Requires network access to UCSC REST API
* **Rate Limits**: UCSC may rate-limit excessive requests
* **Chain Files**: liftOver requires downloading chain files (~1-50MB each) on first use
* **Platform Support**: liftOver binary auto-download supports Linux (x86_64) and macOS (x86_64)

---

## 🧰 Development Tips

- **Run with uv**  
  ```bash
  uv run server.py
  ```
- **Add new tools**  
  Decorate Python functions with `@mcp.tool()` inside `server.py`.
- **Debug locally**  
  Use FastAPI mode (`uv run server.py api`) for quick JSON responses.

---

## 🐛 Troubleshooting

### liftOver binary not found

The binary is auto-downloaded on first use. If it fails:
```bash
# Check platform detection
python -c "import platform; print(platform.system(), platform.machine())"

# Manual download (macOS example)
curl -O https://hgdownload.soe.ucsc.edu/admin/exe/macOSX.x86_64/liftOver
chmod +x liftOver
mv liftOver genomicops/liftover_data/
```

### Chain file download fails

Chain files are fetched from UCSC. Ensure network access to `hgdownload.soe.ucsc.edu`.

### UCSC API timeout

Increase timeout for slow connections:
```bash
curl "http://localhost:8000/tracks/hg38?timeout=30"
```

---

## 📚 References

* [Model Context Protocol](https://modelcontextprotocol.io)
* [FastMCP Documentation](https://gofastmcp.com)
* [UCSC Genome Browser REST API](https://genome.ucsc.edu/goldenPath/help/api.html)
* [UCSC liftOver Tool](https://genome.ucsc.edu/cgi-bin/hgLiftOver)

---

**Author:** Tobias Neumann  
**License:** MIT  
**Version:** 0.1.0