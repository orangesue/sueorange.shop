#!/usr/bin/env python3
"""把 SOCKS5 代理包装成本地 HTTP 代理。

用途：这台 Ubuntu 虚拟机的 VMware NAT 没有转发外网，只能通过
`ssh -R 10808:127.0.0.1:10808` 把宿主机的 SOCKS5 代理接进来。但
`npm` 只认 HTTP(S) 代理（不读 ALL_PROXY 的 socks 协议），所以需要
这样一个本地桥：

    ssh -R 10808:127.0.0.1:10808 <vm> \
        'python3 tools/setup/socks-bridge.py & \
         npm install --proxy=http://127.0.0.1:8899 --https-proxy=http://127.0.0.1:8899'

只监听 127.0.0.1，不对外开放；用完即关。
"""

from __future__ import annotations

import os
import socket
import socketserver
import struct
import threading
from urllib.parse import urlsplit

# 端口可用环境变量覆盖，方便同时开多条隧道时避开冲突
SOCKS_HOST = os.environ.get("BRIDGE_SOCKS_HOST", "127.0.0.1")
SOCKS_PORT = int(os.environ.get("BRIDGE_SOCKS_PORT", "10808"))
LISTEN_HOST = os.environ.get("BRIDGE_LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("BRIDGE_LISTEN_PORT", "8899"))
BUFFER = 65536


def socks5_connect(host: str, port: int) -> socket.socket:
    """经由本地 SOCKS5 连到目标；域名交给代理解析（socks5h 语义）。"""
    sock = socket.create_connection((SOCKS_HOST, SOCKS_PORT), timeout=20)
    sock.sendall(b"\x05\x01\x00")
    if sock.recv(2) != b"\x05\x00":
        raise OSError("SOCKS5 握手失败")

    raw = host.encode("idna") if host.isascii() else host.encode("utf-8")
    request = b"\x05\x01\x00\x03" + bytes([len(raw)]) + raw + struct.pack(">H", port)
    sock.sendall(request)

    header = sock.recv(4)
    if len(header) < 4 or header[1] != 0:
        raise OSError("SOCKS5 连接失败")

    atyp = header[3]
    if atyp == 1:
        sock.recv(4)
    elif atyp == 3:
        sock.recv(sock.recv(1)[0])
    elif atyp == 4:
        sock.recv(16)
    sock.recv(2)

    sock.settimeout(None)
    return sock


def pump(source: socket.socket, target: socket.socket) -> None:
    try:
        while True:
            chunk = source.recv(BUFFER)
            if not chunk:
                break
            target.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            target.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def read_headers(sock: socket.socket) -> tuple[bytes, bytes] | None:
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        buffer += chunk
        if len(buffer) > 1_000_000:
            return None
    head, _, rest = buffer.partition(b"\r\n\r\n")
    return head + b"\r\n\r\n", rest


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(30)
        try:
            parsed = read_headers(self.request)
        except OSError:
            return
        if parsed is None:
            return

        head, rest = parsed
        line = head.split(b"\r\n", 1)[0].decode("latin1")
        parts = line.split()
        if len(parts) < 2:
            return

        method, target = parts[0].upper(), parts[1]

        try:
            if method == "CONNECT":
                host, _, port = target.rpartition(":")
                remote = socks5_connect(host, int(port))
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                if rest:
                    remote.sendall(rest)
            else:
                split = urlsplit(target)
                if not split.hostname:
                    return
                remote = socks5_connect(split.hostname, split.port or 80)
                path = split.path or "/"
                if split.query:
                    path += "?" + split.query
                rewritten = head.replace(target.encode("latin1"), path.encode("latin1"), 1)
                remote.sendall(rewritten + rest)
        except (OSError, ValueError):
            try:
                self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            except OSError:
                pass
            return

        thread = threading.Thread(target=pump, args=(self.request, remote), daemon=True)
        thread.start()
        pump(remote, self.request)
        remote.close()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server((LISTEN_HOST, LISTEN_PORT), ProxyHandler) as server:
        print(f"HTTP 代理已就绪：http://{LISTEN_HOST}:{LISTEN_PORT} -> socks5://{SOCKS_HOST}:{SOCKS_PORT}")
        server.serve_forever()
