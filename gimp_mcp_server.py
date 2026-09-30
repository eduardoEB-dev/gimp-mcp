#!/usr/bin/env python3
# GIMP MCP Server Plugin (GIMP 3.x)
# Starts a socket server inside GIMP so gimp_mcp_client.py (the MCP server) can drive GIMP.
#
# Protocol: newline-delimited JSON over TCP 127.0.0.1:9876.
#   first line:  {"auth": "<token>"}\n  -- token is written to ~/.gimp_mcp_token on start
#   request:  {"type": "...", "params": {...}}\n
#   response: {"status": "success"|"error", ...}\n
# Object refs: images are {"__image__": id}, items (layers, channels, ...) are {"__item__": id}.

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib
from gi.repository import Gio
import io
import hmac
import json
import os
import secrets
import socket
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

HOST = '127.0.0.1'
PORT = 9876
TOKEN_FILE = Path.home() / '.gimp_mcp_token'


def N_(message): return message
def _(message): return GLib.dgettext(None, message)


def to_json(obj):
    """Convert GIMP objects / GLib values to JSON-friendly data."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [to_json(o) for o in obj]
    if isinstance(obj, dict):
        return {str(k): to_json(v) for k, v in obj.items()}
    if isinstance(obj, Gimp.Image):
        return {"__image__": obj.get_id(), "name": obj.get_name()}
    if isinstance(obj, Gimp.Item):
        return {"__item__": obj.get_id(), "type": type(obj).__name__, "name": obj.get_name()}
    return str(obj)


def from_json(obj):
    """Resolve object refs coming from the client back into GIMP objects."""
    if isinstance(obj, list):
        return [from_json(o) for o in obj]
    if isinstance(obj, dict):
        if "__image__" in obj:
            img = Gimp.Image.get_by_id(obj["__image__"])
            if img is None:
                raise ValueError(f"No image with id {obj['__image__']}")
            return img
        if "__item__" in obj:
            item = Gimp.Item.get_by_id(obj["__item__"])
            if item is None:
                raise ValueError(f"No item with id {obj['__item__']}")
            return item
        return {k: from_json(v) for k, v in obj.items()}
    return obj


def get_image(image_id):
    img = Gimp.Image.get_by_id(image_id)
    if img is None:
        raise ValueError(f"No image with id {image_id}")
    return img


class MCPPlugin(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["plug-in-mcp-server"]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        procedure.set_menu_label(_("Start MCP Server"))
        procedure.set_documentation(_("Starts an MCP server to control GIMP externally"),
                                    _("Listens on 127.0.0.1:9876 for commands from the MCP bridge"),
                                    name)
        procedure.set_attribution("gimp-mcp", "gimp-mcp", "2025")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
        procedure.add_menu_path('<Image>/Filters/Development/')
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        # GIMP API calls must run on the plug-in's main thread, and the plug-in process
        # exits as soon as run() returns, so serve requests here in a blocking loop.
        try:
            self.serve()
        except Exception as e:
            return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR,
                                               GLib.Error.new_literal(Gimp.PlugIn.error_quark(), str(e), 0))
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    def serve(self):
        # A fresh random token per session; only processes that can read the user's
        # home dir (i.e. the bridge) can authenticate. Blocks browsers / other users.
        self.token = secrets.token_hex(32)
        fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as tf:
            tf.write(self.token)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT))
        sock.listen(1)
        print(f"MCP server listening on {HOST}:{PORT}")
        self.running = True
        try:
            while self.running:
                client, addr = sock.accept()
                print(f"MCP client connected: {addr}")
                with client:
                    try:
                        self.handle_client(client)
                    except OSError as e:  # timeout, reset, etc. -- keep serving
                        print(f"MCP client error: {e}")
        finally:
            sock.close()
            try:
                TOKEN_FILE.unlink()
            except OSError:
                pass
            print("MCP server stopped")

    def handle_client(self, client):
        client.settimeout(10)  # must authenticate promptly
        f = client.makefile('rwb')
        authed = False
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Hang up on anything that isn't a JSON object (e.g. an HTTP request from a web page).
            try:
                command = json.loads(line.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                print("MCP: rejected non-JSON input, closing connection")
                return
            if not isinstance(command, dict):
                return
            if not authed:
                if not hmac.compare_digest(str(command.get("auth", "")).encode(), self.token.encode()):
                    print("MCP: authentication failed, closing connection")
                    f.write(b'{"status": "error", "message": "authentication failed"}\n')
                    f.flush()
                    return
                authed = True
                client.settimeout(None)
                response = {"status": "success", "result": "authenticated"}
            else:
                response = self.execute_command(command)
            f.write(json.dumps(response).encode('utf-8') + b'\n')
            f.flush()
            if not self.running:
                break

    def execute_command(self, command):
        cmd_type = command.get("type")
        params = command.get("params", {})
        try:
            handler = getattr(self, f"cmd_{cmd_type}", None)
            if handler is None:
                return {"status": "error", "message": f"Unknown command: {cmd_type}"}
            return {"status": "success", "result": to_json(handler(**params))}
        except Exception as e:
            return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

    # ---- commands ----

    def cmd_ping(self):
        return "pong"

    def cmd_stop(self):
        self.running = False
        return "stopping"

    def cmd_call_api(self, api_path, args=None, kwargs=None):
        """Call Gimp.<api_path>(*args, **kwargs), e.g. "Image.get_width" with args [{"__image__": 1}]."""
        target = Gimp
        parts = api_path.split(".")
        if parts[0] == "Gimp":
            parts = parts[1:]
        for part in parts:
            target = getattr(target, part)
        result = target(*from_json(args or []), **from_json(kwargs or {}))
        Gimp.displays_flush()
        return result

    def cmd_exec_python(self, code):
        """Run Python code inside GIMP. `Gimp` is in scope; set `result` to return a value."""
        scope = {"Gimp": Gimp, "GLib": GLib, "result": None}
        out = io.StringIO()
        with redirect_stdout(out):
            exec(code, scope)
        Gimp.displays_flush()
        return {"result": scope.get("result"), "stdout": out.getvalue()}

    def cmd_list_images(self):
        return [{"id": img.get_id(), "name": img.get_name(),
                 "width": img.get_width(), "height": img.get_height()}
                for img in Gimp.get_images()]

    def cmd_get_image_info(self, image_id):
        img = get_image(image_id)
        f = img.get_file()
        return {
            "id": img.get_id(),
            "name": img.get_name(),
            "file": f.get_path() if f else None,
            "width": img.get_width(),
            "height": img.get_height(),
            "base_type": img.get_base_type().value_nick,
            "layers": [{"id": l.get_id(), "name": l.get_name(),
                        "width": l.get_width(), "height": l.get_height(),
                        "visible": l.get_visible()} for l in img.get_layers()],
            "selected_layers": [l.get_id() for l in img.get_selected_layers()],
        }

    def cmd_apply_gaussian_blur(self, image_id, radius=5.0):
        img = get_image(image_id)
        layers = img.get_selected_layers()
        if not layers:
            raise ValueError("No layer selected")
        img.undo_group_start()
        try:
            for drawable in layers:
                flt = Gimp.DrawableFilter.new(drawable, "gegl:gaussian-blur", "Gaussian Blur")
                cfg = flt.get_config()
                cfg.set_property("std-dev-x", float(radius))
                cfg.set_property("std-dev-y", float(radius))
                flt.update()
                drawable.merge_filter(flt)
        finally:
            img.undo_group_end()
        Gimp.displays_flush()
        return f"Applied Gaussian blur (radius {radius}) to {len(layers)} layer(s)"

    def cmd_open_image(self, path):
        img = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(path))
        try:
            Gimp.Display.new(img)
        except Exception:
            pass  # no UI (e.g. gimp-console)
        return {"id": img.get_id(), "name": img.get_name()}

    def cmd_save_image(self, image_id, path):
        img = get_image(image_id)
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(path), None)
        return f"Saved to {path}"


Gimp.main(MCPPlugin.__gtype__, sys.argv)
