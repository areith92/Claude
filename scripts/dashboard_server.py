#!/usr/bin/env python3
"""Serves the dashboard and a small local API so the Approvals page can approve or deny products.
It listens on this computer only (127.0.0.1). Decisions go through the same checks as scripts/research.py.
Usage: python3 scripts/dashboard_server.py [--port 8000]"""
import argparse
import http.server
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research  # noqa: E402
from check_budget import ROOT  # noqa: E402
import watch  # noqa: E402
from store import open_store  # noqa: E402

DASH = ROOT / "dashboard"
TOKEN = secrets.token_urlsafe(24)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DASH), **kw)

    def log_message(self, fmt, *args):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urllib.parse.unquote(self.path.split("?")[0])
        if p == "/api/research":
            return self.reply(200, research.api_state())
        if p == "/api/ops":
            try:
                return self.reply(200, watch.summary())
            except Exception as exc:  # a store problem should show on the page, not crash the server
                return self.reply(500, {"error": str(exc)[:200]})
        if p == "/api/token":
            return self.reply(200, {"token": TOKEN})
        if p.startswith("/research/images/"):
            f = (ROOT / p.lstrip("/")).resolve()
            if research.IMAGES.resolve() not in f.parents or not f.is_file():
                return self.reply(404, {"ok": False})
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self):
        if self.headers.get("X-Dash-Token") != TOKEN:
            return self.reply(403, {"ok": False, "message": "Missing or wrong token. Reload the page."})
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
            return self.reply(403, {"ok": False, "message": "Cross-site request refused."})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 20000)) or b"{}")
            if self.path == "/api/decision":
                if body.get("decision") not in ("approved", "denied"):
                    return self.reply(400, {"ok": False, "message": "decision must be approved or denied"})
                ok, msg = research.decide(body["id"], body["decision"], str(body.get("reason", ""))[:500], bool(body.get("acknowledge")))
                return self.reply(200 if ok else 409, {"ok": ok, "message": msg})
            if self.path == "/api/alert":
                if body.get("status") not in ("acknowledged", "closed"):
                    return self.reply(400, {"ok": False, "message": "status must be acknowledged or closed"})
                n = open_store().update("alerts", {"id": int(body["id"])}, {"status": body["status"]})
                return self.reply(200, {"ok": bool(n), "message": "Saved." if n else "No such alert."})
            if self.path == "/api/confirm":
                research.set_confirm(body["id"], body["field"], body.get("value"))
                return self.reply(200, {"ok": True, "message": "Saved."})
        except (KeyError, ValueError, SystemExit) as exc:
            return self.reply(400, {"ok": False, "message": f"Bad request: {exc}"})
        return self.reply(404, {"ok": False, "message": "Unknown endpoint."})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    if not a.no_build:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_dashboard.py")], cwd=ROOT, capture_output=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Dashboard: http://127.0.0.1:{srv.server_address[1]}  (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
