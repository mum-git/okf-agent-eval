#!/usr/bin/env python3
"""
Lightweight proxy between pi and llama-server.
Captures token usage from API responses and writes to a file.
Listens on port 1235, forwards to llama-server on port 1234.
"""

import json
import sys
import threading
import urllib.request
import http.server
import socketserver

UPSTREAM = "http://127.0.0.1:1234"
TOKEN_LOG = "/tmp/llama_proxy_tokens.log"
lock = threading.Lock()

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Forward to upstream
        req = urllib.request.Request(
            f"{UPSTREAM}{self.path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                response_body = resp.read()
                status = resp.status

                # Try to extract token usage
                try:
                    data = json.loads(response_body)
                    usage = data.get("usage", {})
                    total = usage.get("total_tokens", 0)
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    with lock:
                        with open(TOKEN_LOG, "a") as f:
                            f.write(f"total={total} prompt={prompt_tokens} completion={completion_tokens}\n")
                except (json.JSONDecodeError, KeyError):
                    pass

                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response_body)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1235
    # Clear log file
    with open(TOKEN_LOG, "w") as f:
        f.write("")
    server = ThreadedServer(("127.0.0.1", port), ProxyHandler)
    print(f"Proxy listening on port {port}, forwarding to {UPSTREAM}", file=sys.stderr)
    server.serve_forever()
