import json, time, random
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

analytics_data = {"total_visits": 0, "successful": 0, "chart": []}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        path = self.path

        # --- LOGIN ---
        if path == "/api/login":
            user = data.get("user", [""])[0]
            pw = data.get("pass", [""])[0]
            if user == "admin" and pw == "1234":
                self.respond({"success": True})
            else:
                self.respond({"error": "Invalid login"})
            return

        # --- VISIT SIMULATION ---
        if path == "/api/visit":
            uid = data.get("uid", [""])[0]
            needed = int(data.get("needed", [0])[0])
            success = 0
            logs = []

            for i in range(needed):
                time.sleep(0.02)
                hit_success = random.random() > 0.1
                if hit_success:
                    success += 1
                progress = round((i + 1) / needed * 100, 2)
                logs.append({"step": i + 1, "progress": progress, "success": success})

            # Update analytics
            analytics_data["total_visits"] += needed
            analytics_data["successful"] += success
            analytics_data["chart"].append({
                "timestamp": time.time(),
                "success": success
            })
            if len(analytics_data["chart"]) > 20:
                analytics_data["chart"].pop(0)

            self.respond({
                "uid": uid,
                "success": success,
                "needed": needed,
                "progress": 100,
                "log": logs
            })
            return

        self.respond({"error": "Unknown endpoint"})

    def do_GET(self):
        if self.path == "/api/stats":
            self.respond(analytics_data)
        else:
            self.respond({"message": "Visit system active"})

    def respond(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())