"""Local preview server with Expo Router fallback for browser refreshes."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

DIRECTORY = Path(__file__).resolve().parent.parent / "mobile" / "dist"

class Preview(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route in {"/report", "/team", "/drafts", "/updates", "/settings"}:
            self.path = "/index.html"
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

if __name__ == "__main__":
    print("BioGuard browser preview: http://localhost:8082/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8082), Preview).serve_forever()
