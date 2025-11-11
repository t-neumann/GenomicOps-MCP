[![CI Tests](https://github.com/t-neumann/GenomicOps-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/t-neumann/GenomicOps-MCP/actions/workflows/tests.yml)

# 🧬 GenomicOps-MCP

**GenomicOps-MCP** is a dual-mode Python server that exposes genomic feature operations via:
- 🧠 **Model Context Protocol (MCP)** — for integration with Claude Desktop and other AI clients.
- 🌐 **FastAPI REST API** — for human-readable, local testing and web interaction.

It currently provides tools to query **UCSC genome browser tracks**, including feature overlaps and assembly listings.

---

## 🚀 Features

- **MCP integration:** Claude Desktop and other MCP-compatible LLM clients can call tools like `get_overlapping_features`.
- **FastAPI web API:** Test and debug the same logic locally in a browser or via `curl`.
- **Unified backend:** One codebase (`src/server/mcp_server.py`) supports both modes.
- **FastMCP-powered:** Built with [FastMCP](https://gofastmcp.com) for standard-compliant and rapid MCP development.

---

## 📁 Project Structure

```
GenomicOps-MCP/
├── src/
│   └── server/
│       ├── mcp_server.py        # Main MCP + FastAPI server
│       └── tools.py             # UCSC tools and helper functions
├── pyproject.toml               # Managed by uv (Python project metadata)
├── uv.lock                      # uv dependency lockfile
├── .gitignore
└── README.md
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

## 🧠 Running in MCP Mode (for Claude Desktop)

Run the server as an **MCP endpoint**:

```bash
uv run src/server/mcp_server.py
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

---

### 🧩 Add to Claude Desktop

To connect this MCP to Claude Desktop:

#### Option 1: Manual Configuration

Add this entry to your `claude_desktop_config.json`:

```json
{
"ucsc-mcp": {
      "command": "/Users/tobias.neumann/.local/bin/uv",
      "args": [
        "run",
        "--project",
        "/Users/tobias.neumann/dev/GenomicOps-MCP",
        "--with",
        "fastmcp",
        "fastmcp",
        "run",
        "/Users/tobias.neumann/dev/GenomicOps-MCP/src/server/mcp_server.py"
      ],
      "env": {},
      "transport": "stdio",
      "type": null,
      "cwd": null,
      "timeout": null,
      "description": null,
      "icon": null,
      "authentication": null
    }
}
```

Then restart Claude Desktop — it should detect `ucsc-mcp` and register the `get_overlapping_features` tool.

#### Option 2: FastMCP CLI (Recommended)

You can install the server directly into Claude Desktop with one command:

```bash
fastmcp install claude-desktop src/server/mcp_server.py \
  --python 3.11 \
  --project /Users/YOUR_USERNAME/dev/GenomicOps-MCP
```

---

## 🌐 Running in FastAPI Mode (for local testing)

If you want to expose the same functionality as a REST API, use the `api` flag:

```bash
uv run src/server/mcp_server.py api
```

Then open your browser at:
👉 [http://localhost:8000/docs](http://localhost:8000/docs)

You’ll see interactive FastAPI documentation (Swagger UI).

### Example endpoints:

| Method | Endpoint             | Description |
|--------|----------------------|--------------|
| `POST` | `/overlaps`          | Query overlapping genomic features |
| `GET`  | `/assemblies`        | List supported genome assemblies |

---

## 🧪 Example Usage (API)

**POST /overlaps**
```bash
curl -X POST http://localhost:8000/overlaps \
  -H "Content-Type: application/json" \
  -d '{"region": "chr1:1000-2000", "assembly": "hg38"}'
```

**GET /assemblies**
```bash
curl http://localhost:8000/assemblies
```

---

## 🧰 Development Tips

- **Run with uv**  
  ```bash
  uv run src/server/mcp_server.py
  ```
- **Add new tools**  
  Decorate Python functions with `@mcp.tool()` inside `mcp_server.py`.
- **Debug locally**  
  Use FastAPI mode (`uv run src/server/mcp_server.py api`) for quick JSON responses.

---

## 📚 References

- [Model Context Protocol Docs](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://gofastmcp.com)
- [Claude Desktop MCP Guide](https://modelcontextprotocol.io/docs/tools/claude)

---

**Author:** Tobias Neumann  
**License:** MIT  
**Version:** 0.1.0
