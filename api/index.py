# api/index.py
import json
import os
import ssl
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Configure real API template (you gave)
VISIT_API_TEMPLATE = os.environ.get(
    "VISIT_API_TEMPLATE",
    "https://visit-api-by-digi.vercel.app/visit?uid={uid}&server_name=ind"
)

# Allow insecure for some hosts if necessary
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "1234")

class handler(BaseHTTPRequestHandler):
    def _json_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._json_headers()
        self.wfile.write(b"{}")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode()
        data = parse_qs(raw)
        path = self.path

        # Admin login
        if path == "/api/login":
            user = (data.get("user") or [""])[0]
            pw = (data.get("pass") or [""])[0]
            if user == ADMIN_USER and pw == ADMIN_PASS:
                self._json_headers(200)
                self.wfile.write(json.dumps({"ok": True}).encode())
            else:
                self._json_headers(401)
                self.wfile.write(json.dumps({"ok": False, "error": "invalid credentials"}).encode())
            return

        # Hit (init / poll)
        if path == "/api/hit":
            uid = (data.get("uid") or [""])[0]
            action = (data.get("action") or ["poll"])[0]  # init | poll
            if not uid:
                self._json_headers(400)
                self.wfile.write(json.dumps({"error": "uid required"}).encode()); return

            url = VISIT_API_TEMPLATE.format(uid=uid)
            try:
                req = Request(url, headers={"User-Agent": "VisitPanel/1.0"})
                with urlopen(req, context=ssl_ctx, timeout=15) as resp:
                    raw_body = resp.read().decode("utf-8", errors="ignore")
                    try:
                        api_json = json.loads(raw_body)
                    except Exception:
                        api_json = {"raw": raw_body}

                    # parse SuccessfulVisits if present
                    succ = None
                    if isinstance(api_json, dict):
                        succ = api_json.get("SuccessfulVisits")
                        # try convert to int
                        try:
                            if succ is not None:
                                succ = int(succ)
                        except Exception:
                            # keep as-is if not convertible
                            pass

                    out = {
                        "ok": True,
                        "action": action,
                        "api": api_json,
                        "SuccessfulVisits": succ
                    }
                    self._json_headers(200)
                    self.wfile.write(json.dumps(out).encode())
                    return

            except HTTPError as e:
                self._json_headers(502)
                self.wfile.write(json.dumps({"error": "upstream_http", "code": e.code, "msg": str(e)}).encode())
                return
            except URLError as e:
                self._json_headers(502)
                self.wfile.write(json.dumps({"error": "upstream_url", "msg": str(e)}).encode())
                return
            except Exception as e:
                self._json_headers(500)
                self.wfile.write(json.dumps({"error": "exception", "msg": str(e)}).encode())
                return

        # unknown
        self._json_headers(404)
        self.wfile.write(json.dumps({"error": "unknown endpoint"}).encode())

    def do_GET(self):
        # health check
        if self.path.startswith("/api/health"):
            self._json_headers(200)
            self.wfile.write(json.dumps({"ok": True}).encode()); return
        self._json_headers(404)
        self.wfile.write(json.dumps({"error": "GET not supported on this endpoint"}).encode())
