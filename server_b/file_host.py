from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class FileHost:
    def __init__(self, directory: str | Path, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.directory = Path(directory)
        self.host = host
        self.port = port
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(self.directory))
        server = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
