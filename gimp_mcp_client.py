#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2"]
# ///
# GIMP MCP bridge: an MCP server (stdio) that forwards tool calls to the
# gimp_mcp_server.py plug-in running inside GIMP on 127.0.0.1:9876.
# Run with: uv run gimp_mcp_client.py

import json
import logging
import socket
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

# stdout is the MCP stdio channel, so logs must go to stderr.
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GimpMCPServer")


class GimpConnection:
    def __init__(self, host='127.0.0.1', port=9876, timeout=120):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.file = None

    def connect(self):
        if self.sock:
            return
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            self.file = self.sock.makefile('rwb')
            logger.info(f"Connected to GIMP at {self.host}:{self.port}")
        except OSError as e:
            self.close()
            raise ConnectionError(
                "Could not connect to GIMP. Open GIMP and run Filters > Development > Start MCP Server."
            ) from e

    def close(self):
        for obj in (self.file, self.sock):
            try:
                if obj:
                    obj.close()
            except OSError:
                pass
        self.sock = None
        self.file = None

    def send_command(self, command_type, params=None):
        # One retry so a GIMP restart doesn't require restarting the MCP server.
        for attempt in (1, 2):
            self.connect()
            try:
                self.file.write(json.dumps({"type": command_type, "params": params or {}}).encode('utf-8') + b'\n')
                self.file.flush()
                line = self.file.readline()
                if not line:
                    raise ConnectionError("GIMP closed the connection")
                return json.loads(line.decode('utf-8'))
            except (OSError, ConnectionError) as e:
                logger.error(f"Communication error: {e}")
                self.close()
                if attempt == 2:
                    raise ConnectionError(f"Error communicating with GIMP: {e}") from e


_gimp_connection = GimpConnection()


def gimp(command_type: str, **params) -> str:
    try:
        result = _gimp_connection.send_command(command_type, params)
    except Exception as e:
        return f"Error: {e}"
    if result.get("status") == "success":
        return json.dumps(result.get("result"), indent=2)
    return f"Error: {result.get('message')}\n{result.get('traceback', '')}".rstrip()


mcp = FastMCP("GimpMCP", instructions=(
    "Controls a running GIMP 3 instance. Image IDs come from list_images. "
    "Prefer the specific tools; use exec_python for anything else (GIMP 3 PyGObject API, `Gimp` in scope)."
))


@mcp.tool()
def list_images() -> str:
    """List all open images in GIMP (id, name, width, height)."""
    return gimp("list_images")


@mcp.tool()
def get_image_info(image_id: int) -> str:
    """Get details (size, file, layers, selected layers) of an open image."""
    return gimp("get_image_info", image_id=image_id)


@mcp.tool()
def open_image(path: str) -> str:
    """Open an image file in GIMP and show it in a new display. Returns its id."""
    return gimp("open_image", path=path)


@mcp.tool()
def save_image(image_id: int, path: str) -> str:
    """Save/export an image to a file. Format is chosen by extension (.png, .jpg, .xcf, ...)."""
    return gimp("save_image", image_id=image_id, path=path)


@mcp.tool()
def apply_gaussian_blur(image_id: int, radius: float = 5.0) -> str:
    """Apply a Gaussian blur to the selected layer(s) of an image."""
    return gimp("apply_gaussian_blur", image_id=image_id, radius=radius)


@mcp.tool()
def call_api(api_path: str, args: list[Any] | None = None, kwargs: dict[str, Any] | None = None) -> str:
    """Call any GIMP 3 API function: Gimp.<api_path>(*args, **kwargs).

    Pass images as {"__image__": id} and layers/items as {"__item__": id};
    results use the same form. Examples:
    - api_path="get_images"
    - api_path="Image.get_width", args=[{"__image__": 1}]
    - api_path="Item.set_visible", args=[{"__item__": 2}, false]
    """
    return gimp("call_api", api_path=api_path, args=args or [], kwargs=kwargs or {})


@mcp.tool()
def exec_python(code: str) -> str:
    """Execute Python code inside GIMP (GIMP 3 PyGObject API). `Gimp`, `GLib` are in scope.
    Assign to `result` to return a value; print() output is returned too.
    Example: result = [i.get_name() for i in Gimp.get_images()]
    """
    return gimp("exec_python", code=code)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
