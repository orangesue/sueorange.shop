#!/usr/bin/env python3
"""试探 QZone 消息/动态接口的参数组合，找出哪种返回「与我相关」的记录。

排查接口用，不属于日常流程：

    python probe_feeds.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qz_archive.api import DESKTOP_UA, QZONE_BASE  # noqa: E402
from qz_archive.cookie import read_cookie_file  # noqa: E402
from qz_archive.parse import decode_bytes, parse_feeds_payload  # noqa: E402

FEEDS_URL = QZONE_BASE + "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds2_html_pav_all"
UIN_IN_ID = re.compile(r"fct_(\d+)_")

# 候选参数组合：QQ 空间的消息页/动态页用的是不同 type/refer
VARIANTS: list[tuple[str, dict[str, object]]] = [
    ("type=all refer=msg", {"type": "all", "refer": "msg"}),
    ("type=msg refer=msg", {"type": "msg", "refer": "msg"}),
    ("type=all refer=feed", {"type": "all", "refer": "feed"}),
    ("type=mood refer=msg", {"type": "mood", "refer": "msg"}),
    ("type=all refer=msg +begin/end", {"type": "all", "refer": "msg", "begin_time": 0, "end_time": 0}),
    ("type=all refer=msg +notifi", {"type": "all", "refer": "msg", "getnotifi": 1}),
    ("refer=msg only", {"refer": "msg"}),
    ("type=shuoshuo", {"type": "shuoshuo", "refer": "msg"}),
]


def summarize(markup: str, self_uin: str) -> str:
    soup = BeautifulSoup(markup, "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).split())[:70]
    ids = UIN_IN_ID.findall(str(soup))
    mine = "★我" if self_uin in ids else "  "
    return f"{mine} uins={sorted(set(ids))[:3]} | {text}"


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

    base = {
        "uin": credentials.uin,
        "getappnotification": 1,
        "getnotifi": 1,
        "hasunreadnotice": 1,
        "g_tk": credentials.gtk,
    }

    parser_args = sys.argv[1:]
    if parser_args and parser_args[0] == "--history":
        pages = int(parser_args[1]) if len(parser_args) > 1 else 30
        return history(session, credentials, pages)
    if parser_args and parser_args[0] == "--windowing":
        return windowing(session, credentials)
    if parser_args and parser_args[0] == "--qzfl":
        return qzfl(session, credentials)

    for name, extra in VARIANTS:
        params = {**base, **extra}
        try:
            response = session.get(FEEDS_URL, params=params, timeout=25)
            text = decode_bytes(response.content)
        except requests.RequestException as error:
            print(f"\n### {name}: 请求失败 {error}")
            continue

        payload = parse_feeds_payload(text)
        items = ((payload.get("data") or {}).get("data") or []) if isinstance(payload, dict) else []
        print(f"\n### {name}  http={response.status_code}  长度={len(text)}  条目={len(items)}")

        main_info = (payload.get("data") or {}).get("main") if isinstance(payload, dict) else None
        print(f"    main={main_info}")

        for index, item in enumerate(items[:3]):
            if isinstance(item, dict):
                print(f"    #{index} {summarize(item.get('html') or '', credentials.uin)}")

    return 0


def history(session: requests.Session, credentials, pages: int) -> int:
    """沿着时间轴往回翻，统计每页里出现的 uin，看自己的说说会不会出现在动态流里。"""
    from datetime import datetime, timezone

    base = {
        "uin": credentials.uin,
        "getappnotification": 1,
        "getnotifi": 1,
        "hasunreadnotice": 1,
        "type": "all",
        "refer": "msg",
        "g_tk": credentials.gtk,
    }

    begin_time = int(datetime.now(tz=timezone.utc).timestamp())
    seen: dict[str, int] = {}
    self_posts: list[str] = []
    earliest_seen = begin_time

    for page in range(pages):
        params = {**base, "begin_time": begin_time, "end_time": 0}
        response = session.get(FEEDS_URL, params=params, timeout=25)
        text = decode_bytes(response.content)
        payload = parse_feeds_payload(text)
        items = ((payload.get("data") or {}).get("data") or []) if isinstance(payload, dict) else []

        stamps: list[int] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            markup = item.get("html") or ""
            uins = UIN_IN_ID.findall(markup)
            for uin in set(uins):
                seen[uin] = seen.get(uin, 0) + 1
            if credentials.uin in uins:
                preview = " ".join(
                    BeautifulSoup(markup, "html.parser").get_text(" ", strip=True).split()
                )[:60]
                self_posts.append(f"abstime={item.get('abstime')} {preview}")
            try:
                stamps.append(int(item.get("abstime") or 0))
            except (TypeError, ValueError):
                pass

        if not stamps:
            print(f"第 {page + 1} 页没有可用时间戳，停止")
            break

        newest = max(stamps)
        oldest = min(stamps)
        if page < 3 or page % 5 == 0:
            print(
                f"第 {page + 1:>3} 页  条目={len(items):>2}  "
                f"时间 {_fmt(oldest)} ~ {_fmt(newest)}"
            )

        if oldest >= earliest_seen:
            print("时间戳没有继续往前，停止")
            break
        earliest_seen = oldest
        begin_time = oldest - 1

    print("\n出现过的 uin（前 20）：")
    for uin, count in sorted(seen.items(), key=lambda kv: -kv[1])[:20]:
        mine = "  ★ 这是你自己" if uin == credentials.uin else ""
        print(f"  {uin}: {count} 条{mine}")

    print(f"\n属于你自己的动态条数：{len(self_posts)}")
    for entry in self_posts[:10]:
        print(f"  {entry}")

    return 0


def _fmt(timestamp: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _fetch(session, credentials, **extra):
    """按给定参数取一页，返回 (条目, 时间戳, 属于我的条数, 原始文本)。"""
    base = {
        "uin": credentials.uin,
        "getappnotification": 1,
        "getnotifi": 1,
        "hasunreadnotice": 1,
        "type": "all",
        "refer": "msg",
        "g_tk": credentials.gtk,
    }
    response = session.get(FEEDS_URL, params={**base, **extra}, timeout=25)
    text = decode_bytes(response.content)
    payload = parse_feeds_payload(text)
    items = ((payload.get("data") or {}).get("data") or []) if isinstance(payload, dict) else []

    stamps: list[int] = []
    self_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            stamps.append(int(item.get("abstime") or 0))
        except (TypeError, ValueError):
            pass
        if credentials.uin in UIN_IN_ID.findall(item.get("html") or ""):
            self_count += 1

    return items, stamps, self_count, text


def windowing(session, credentials) -> int:
    """试探两种翻页方式：offset 递增、以及滑动 begin_time/end_time 时间窗。"""
    from datetime import datetime, timedelta, timezone

    print("=== offset 递增 ===")
    for offset in (0, 7, 14, 21, 50):
        items, stamps, self_count, _ = _fetch(session, credentials, offset=offset)
        span = f"{_fmt(min(stamps))} ~ {_fmt(max(stamps))}" if stamps else "-"
        print(f"  offset={offset:<3} 条目={len(items):<3} 属于我={self_count}  时间 {span}")

    print("\n=== 滑动时间窗 ===")
    now = datetime.now(tz=timezone.utc)
    windows = [
        ("最近 1 天", now - timedelta(days=1), now),
        ("1~7 天前", now - timedelta(days=7), now - timedelta(days=1)),
        ("7~30 天前", now - timedelta(days=30), now - timedelta(days=7)),
        ("30~180 天前", now - timedelta(days=180), now - timedelta(days=30)),
        ("1~3 年前", now - timedelta(days=1095), now - timedelta(days=365)),
    ]
    for label, begin, end in windows:
        items, stamps, self_count, text = _fetch(
            session,
            credentials,
            begin_time=int(begin.timestamp()),
            end_time=int(end.timestamp()),
        )
        span = f"{_fmt(min(stamps))} ~ {_fmt(max(stamps))}" if stamps else "-"
        print(
            f"  {label:<12} 条目={len(items):<3} 属于我={self_count}  "
            f"时间 {span}  (响应 {len(text)} 字符)"
        )

    return 0


def qzfl(session, credentials) -> int:
    """页面上那条请求带了个 qzfl_s 参数，试试补上它会不会返回「消息」而不是好友动态。"""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone.utc)
    variants = [
        ("qzfl_s=1", {"qzfl_s": 1}),
        ("qzfl_s=s", {"qzfl_s": "s"}),
        ("qzfl_s=1 + type=msg", {"qzfl_s": 1, "type": "msg", "refer": "msg"}),
        (
            "qzfl_s=1 + 最近1天",
            {
                "qzfl_s": 1,
                "begin_time": int((now - timedelta(days=1)).timestamp()),
                "end_time": int(now.timestamp()),
            },
        ),
        ("带 X-Requested-With", {"qzfl_s": 1, "_xrw": True}),
    ]

    for label, extra in variants:
        headers = {}
        if extra.pop("_xrw", False):
            headers["X-Requested-With"] = "XMLHttpRequest"
        items, stamps, self_count, text = _fetch(session, credentials, **extra)
        print(f"\n### {label}  条目={len(items)} 属于我={self_count} 响应={len(text)} 字符")
        for index, item in enumerate(items[:3]):
            if isinstance(item, dict):
                print(f"    #{index} {summarize(item.get('html') or '', credentials.uin)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
