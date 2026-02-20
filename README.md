# Kruncher MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes [Kruncher](https://kruncher.ai) project and analysis data as tools for AI assistants like Claude.

## Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all your Kruncher projects (paginated) |
| `get_analysis_detail` | Fetch the full report for a given `analysisId` |
| `get_latest_analysis_for_project` | Fetch the most recent analysis report for a project |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
cp .env.example .env
# Edit .env and set KRUNCHER_API_KEY=<your key>
export KRUNCHER_API_KEY=your_api_key_here
```

### 3. Run the server

```bash
python server.py
```

## Usage with Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "kruncher": {
      "command": "python",
      "args": ["/path/to/kruncher-mcp-example/server.py"],
      "env": {
        "KRUNCHER_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Usage with Cursor / other MCP clients

Point your MCP client at `python server.py` with `KRUNCHER_API_KEY` set in the environment.

## API Reference

Base URL: `https://api.kruncher.ai/api/integration`

Authentication: `Authorization: <api_key>` header (no `Bearer` prefix needed).

### Endpoints used

- `GET /projects?page=0&pageSize=20` — paginated project list
- `GET /analysis/detail?analysisId=<id>` — full analysis report
