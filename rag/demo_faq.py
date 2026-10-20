import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from chat_api import handle_chat, handle_solved
from faq_agent import _get_retriever

CONFIG_HOST = "127.0.0.1"
CONFIG_PORT = 8000
CONFIG_PAGE_PATH = os.path.join(os.path.dirname(__file__), "web", "index.html")
CONFIG_MAX_BODY_BYTES = 20000

_agent_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, data):
        self._send(status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path != "/":
            self._send_json(404, {"error": "Not found."})
            return
        with open(CONFIG_PAGE_PATH, "rb") as handle:
            self._send(200, "text/html; charset=utf-8", handle.read())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > CONFIG_MAX_BODY_BYTES:
            self._send_json(413, {"error": "The request is too large."})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send_json(400, {"error": "The body is not valid JSON."})
            return

        if self.path == "/api/chat":
            handler = handle_chat
        elif self.path == "/api/solved":
            handler = handle_solved
        else:
            self._send_json(404, {"error": "Not found."})
            return
        try:
            with _agent_lock:
                status, body = handler(payload)
        except Exception:
            self._send_json(500, {"error": "Something went wrong answering. Try again."})
            return
        self._send_json(status, body)

    def log_message(self, format, *args):
        return


def main():
    print("Loading the embedding model...")
    _get_retriever()
    server = ThreadingHTTPServer((CONFIG_HOST, CONFIG_PORT), Handler)
    print("Demo running at http://" + CONFIG_HOST + ":" + str(CONFIG_PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


main()
