"""Minimal mock backend to let the OpenWebUI frontend boot for preview."""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

MOCK_CONFIG = {
    "status": True,
    "name": "DBiz GPT",
    "version": "0.11.3",
    "default_locale": "en-US",
    "oauth": {"providers": {}},
    "features": {
        "enable_signup": True,
        "enable_login_form": True,
        "enable_web_search": False,
        "enable_image_generation": False,
        "enable_community_sharing": False,
        "enable_admin_export": True,
        "enable_admin_chat_access": True,
    },
    "default_models": "",
    "default_prompt_suggestions": [],
    "audio": {"tts": {"engine": ""}, "stt": {"engine": ""}},
    "permissions": {"chat": {"deletion": True}},
}

MOCK_USER = {
    "id": "mock-user-001",
    "email": "demo@dbiz.com",
    "name": "Demo User",
    "role": "admin",
    "profile_image_url": "",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if not path:
            path = "/"

        if path == "/api/config":
            self._json(MOCK_CONFIG)
        elif path in ("/api/v1/auths", "/api/v1/auths/"):
            self._json(MOCK_USER)
        elif path in ("/api/models", "/api/v1/models"):
            self._json({"data": []})
        elif path == "/api/v1/chats/pinned":
            self._json([])
        elif path.startswith("/api/v1/chats/tags"):
            self._json([])
        elif path.startswith("/api/v1/chats"):
            self._json([])
        elif path.startswith("/api/v1/tools"):
            self._json([])
        elif path.startswith("/api/v1/terminals"):
            self._json([])
        elif path.startswith("/api/v1/functions"):
            self._json([])
        elif path.startswith("/api/v1/prompts"):
            self._json([])
        elif path.startswith("/api/v1/knowledge"):
            self._json([])
        elif path.startswith("/api/v1/channels"):
            self._json([])
        elif path.startswith("/api/v1/users"):
            self._json([MOCK_USER])
        elif path.startswith("/api/v1/configs"):
            self._json({})
        elif path.startswith("/api/v1/evaluations"):
            self._json([])
        elif path.startswith("/api/v1/folders"):
            self._json([])
        elif path.startswith("/api/v1/memories"):
            self._json([])
        elif path.startswith("/api/v1/groups"):
            self._json([])
        elif path.startswith("/api/v1/finance"):
            self._json({"items": [], "total": 0})
        elif path == "/health":
            self._json({"status": True})
        elif path.startswith("/api/"):
            self._json([])
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_length)
        if path in ("/api/v1/auths/signin", "/api/v1/auths/signup"):
            self._json({**MOCK_USER, "token": "mock-token-for-preview"})
        elif path.startswith("/api/"):
            self._json({"status": "ok"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        content_length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_length)
        self._json({"status": "ok"})

    def do_DELETE(self):
        self._json({"status": "ok"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def log_message(self, format, *args):
        print(f"  {args[0]}", flush=True)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8080), Handler)
    print("Mock backend running on http://127.0.0.1:8080", flush=True)
    sys.stdout.flush()
    server.serve_forever()
