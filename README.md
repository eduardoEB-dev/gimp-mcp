# GIMP-MCP

Control GIMP 3 from AI assistants (Claude Desktop, Claude Code, any MCP client) via the Model Context Protocol.

## How it works

```
MCP client  <--stdio-->  gimp_mcp_client.py  <--TCP 127.0.0.1:9876-->  gimp_mcp_server.py (GIMP plug-in)
```

- `gimp_mcp_server.py` — GIMP 3 plug-in. Runs inside GIMP and executes commands.
- `gimp_mcp_client.py` — MCP server your AI client launches. Forwards tool calls to the plug-in.

## Requirements

- **GIMP 3.0+** (tested on 3.2.4). GIMP 2.10 is not supported.
- [uv](https://docs.astral.sh/uv/) (installs the `mcp` dependency automatically), or Python 3.10+ with `pip install "mcp<2"`.

## Install

1. Copy the plug-in into its own folder (the folder name must match the file name):
   - Windows: `%APPDATA%\GIMP\3.2\plug-ins\gimp_mcp_server\gimp_mcp_server.py`
   - Linux: `~/.config/GIMP/3.2/plug-ins/gimp_mcp_server/gimp_mcp_server.py` (then `chmod +x` it)
   - macOS: `~/Library/Application Support/GIMP/3.2/plug-ins/gimp_mcp_server/gimp_mcp_server.py`

   Use your GIMP version folder (`3.0`, `3.2`, ...).

2. Restart GIMP, then run **Filters > Development > Start MCP Server**. GIMP stays usable while it listens.

3. Register the MCP server with your client.

   Claude Code:
   ```bash
   claude mcp add gimp -- uv run D:/gimp-mcp/gimp_mcp_client.py
   ```

   Claude Desktop (`claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "gimp": {
         "command": "uv",
         "args": ["run", "D:/gimp-mcp/gimp_mcp_client.py"]
       }
     }
   }
   ```

## Tools

| Tool | Description |
|---|---|
| `list_images` | Open images (id, name, size) |
| `get_image_info` | Size, file, layers, selected layers |
| `open_image` | Open a file in GIMP |
| `save_image` | Save/export (format by extension) |
| `apply_gaussian_blur` | Blur selected layer(s) |
| `call_api` | Call any `Gimp.*` function. Images as `{"__image__": id}`, layers/items as `{"__item__": id}` |
| `exec_python` | Run Python inside GIMP (`Gimp` in scope; set `result` to return a value) |

Example prompts: "list my open images", "blur image 1 with radius 8 and save it to D:/out.png".

## Security

- Listens on `127.0.0.1` only.
- Each session writes a random token to `~/.gimp_mcp_token`; clients must send it first or get disconnected. Blocks web pages and other users.
- Any non-JSON input (e.g. an HTTP request) closes the connection immediately.
- `exec_python` / `call_api` still run arbitrary code in GIMP, so don't auto-approve them in your MCP client, and only start the server when you need it.

## License

GPL-3.0 — see [LICENSE](LICENSE).
