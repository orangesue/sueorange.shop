#!/usr/bin/env python3
"""试探 emotion_cgi_msglist_v6 的翻页边界：pos 到多少会被拒。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qz_archive.api import DESKTOP_UA, QZONE_BASE  # noqa: E402
from qz_archive.cookie import read_cookie_file  # noqa: E402
from qz_archive.parse import decode_bytes, parse_msglist_jsonp  # noqa: E402

HOSTS = {
    "user": QZONE_BASE + "/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6",
    "h5": "https://h5.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6",
}


def main() -> int:
    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}",
            "Cookie": credentials.raw_cookie,
        }
    )

    def probe(host: str, pos: int, num: int, extra: dict | None = None) -> None:
        params = {
            "uin": credentials.uin,
            "ftype": 0,
            "sort": 0,
            "pos": pos,
            "num": num,
            "replynum": 100,
            "g_tk": credentials.gtk,
            "callback": "_preloadCallback",
            "code_version": 1,
            "format": "jsonp",
            "need_private_comment": 1,
        }
        if extra:
            params.update(extra)
        try:
            response = session.get(HOSTS[host], params=params, timeout=25)
        except requests.RequestException as error:
            print(f"  [{host}] pos={pos:<4} num={num:<3} 请求异常 {error}")
            return

        text = decode_bytes(response.content)
        payload = parse_msglist_jsonp(text)
        total = payload.get("total")
        items = payload["msglist"]
        first = items[0].get("tid") if items else "-"
        print(
            f"  [{host}] pos={pos:<4} num={num:<3} http={response.status_code} "
            f"条数={len(items):<3} total={total} 首条tid={first}"
        )

    print("=== user.qzone.qq.com 的 pos 边界 ===")
    for pos in (700, 780, 790, 795, 800, 810):
        probe("user", pos, 20)

    print("\n=== 换个 num 试试 pos=800 ===")
    for num in (5, 10, 15):
        probe("user", 800, num)

    print("\n=== 换 h5.qzone.qq.com 主机 ===")
    for pos in (780, 800, 1000):
        probe("h5", pos, 20)

    print("\n=== 加 begintime / endtime ===")
    for extra in ({"begintime": 0}, {"endtime": 0}, {"begintime": 0, "endtime": 4102416000}):
        probe("user", 800, 20, extra)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

