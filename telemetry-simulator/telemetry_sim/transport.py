"""Where packets go. Swappable so the final transport can be decided later.

--output stdout                 JSON Lines on standard output (default)
--output file:run.jsonl         JSON Lines file
--output udp://127.0.0.1:5005   one JSON packet per UDP datagram
--output http://host:8000/ingest  one HTTP POST per packet (application/json)
"""
from __future__ import annotations

import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


class Sink:
    kind = "stdout"
    realtime_default = False

    def send(self, line: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class StdoutSink(Sink):
    def send(self, line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


class FileSink(Sink):
    kind = "file"

    def __init__(self, path: str):
        self.fh = open(path, "w", encoding="utf-8")

    def send(self, line: str) -> None:
        self.fh.write(line + "\n")

    def close(self) -> None:
        self.fh.close()


class UdpSink(Sink):
    kind = "udp"
    realtime_default = True

    def __init__(self, host: str, port: int):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, line: str) -> None:
        self.sock.sendto(line.encode("utf-8"), self.addr)

    def close(self) -> None:
        self.sock.close()


class HttpSink(Sink):
    kind = "http"
    realtime_default = True

    def __init__(self, url: str, timeout: float = 2.0):
        self.url, self.timeout, self.failures = url, timeout, 0

    def send(self, line: str) -> None:
        req = urllib.request.Request(self.url, data=line.encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=self.timeout).close()
        except (urllib.error.URLError, OSError) as exc:
            self.failures += 1
            if self.failures <= 5 or self.failures % 100 == 0:
                print(f"[http] send failed ({self.failures}): {exc}", file=sys.stderr)


def make_sink(spec: str) -> Sink:
    if spec in ("-", "stdout"):
        return StdoutSink()
    if spec.startswith("file:"):
        return FileSink(spec[5:])
    if spec.startswith("udp://"):
        u = urlparse(spec)
        return UdpSink(u.hostname or "127.0.0.1", u.port or 5005)
    if spec.startswith(("http://", "https://")):
        return HttpSink(spec)
    raise ValueError(f"unknown output {spec!r} (use stdout, file:PATH, udp://HOST:PORT or http://URL)")
