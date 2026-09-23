#!/usr/bin/env python3
"""把 --dump-raw 保存的原始响应解码成人能看懂的样子。

接口字段一旦变化，先用它看一眼真实结构，再去改 qz_archive/parse.py。

    python inspect_raw.py --feeds   ~/public/data/raw/feeds-001.txt
    python inspect_raw.py --msglist ~/public/data/raw/msglist-001.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qz_archive.parse import (  # noqa: E402
    LAST_JSON5_ERROR,
    parse_feeds_payload,
    parse_msglist_jsonp,
    strip_callback,
)
from bs4 import BeautifulSoup  # noqa: E402

ITEM_FIELDS = (
    "appid",
    "typeid",
    "key",
    "abstime",
    "feedstime",
    "uin",
    "nickname",
    "title",
    "summary",
    "dataonly",
    "oprType",
)


def html_preview(markup: str, limit: int = 400) -> str:
    text = BeautifulSoup(markup or "", "html.parser").get_text(" ", strip=True)
    return text[:limit]


def inspect_feeds(path: Path, limit: int) -> None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    print(f"文件大小: {len(raw)} 字符")
    print(f"回调外壳: {raw[:40]!r}")

    payload = parse_feeds_payload(raw)
    if LAST_JSON5_ERROR[0]:
        print(f"json5 解析失败（已用正则兜底）: {LAST_JSON5_ERROR[0]}")
    outer = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(outer, dict):
        print("!! 没解析出 data 字段，原始内容开头：")
        print(raw[:600])
        return

    print(f"main: {outer.get('main')}")
    items = outer.get("data") or []
    print(f"条目数: {len(items)}")

    for index, item in enumerate(items[:limit]):
        if not isinstance(item, dict):
            continue
        meta = {key: item.get(key) for key in ITEM_FIELDS if item.get(key) not in (None, "")}
        print(f"\n--- #{index} {meta}")
        markup = item.get("html") or ""
        print(f"    html 长度 {len(markup)}，正文预览：{html_preview(markup)!r}")


def dump_item_html(path: Path, index: int) -> None:
    """把某一条目的 HTML 原样打印出来，用来对照真实标签结构。"""
    payload = parse_feeds_payload(path.read_text(encoding="utf-8", errors="replace"))
    items = (payload.get("data") or {}).get("data") or []
    if index >= len(items):
        print(f"只有 {len(items)} 条，取不到 #{index}")
        return
    print(items[index].get("html") or "")


def inspect_msglist(path: Path, limit: int) -> None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    payload = parse_msglist_jsonp(raw)
    items = payload["msglist"]
    print(f"文件大小: {len(raw)} 字符，说说条数: {len(items)}，total={payload['total']}")
    for index, item in enumerate(items[:limit]):
        if not isinstance(item, dict):
            continue
        print(f"\n--- #{index} tid={item.get('tid')} 时间={item.get('created_time')}")
        print(f"    正文: {(item.get('content') or '')[:120]!r}")
        print(f"    配图数: {len(item.get('pic') or [])}  评论数: {len(item.get('commentlist') or [])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="解码 --dump-raw 保存的原始响应")
    parser.add_argument("--feeds", type=Path)
    parser.add_argument("--msglist", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--strip-demo", action="store_true")
    parser.add_argument(
        "--dump-html",
        type=int,
        default=None,
        metavar="N",
        help="把第 N 条互动条目的 HTML 原样打印出来",
    )
    args = parser.parse_args()

    if args.dump_html is not None:
        dump_item_html(args.feeds, args.dump_html)
        return 0

    if args.strip_demo:
        sample = strip_callback('_Callback({"a":1});')
        print(f"strip_callback 自检: {sample}")

    if not args.feeds and not args.msglist:
        parser.print_help()
        return 1

    if args.feeds:
        print(f"===== feeds: {args.feeds} =====")
        inspect_feeds(args.feeds, args.limit)
    if args.msglist:
        print(f"===== msglist: {args.msglist} =====")
        inspect_msglist(args.msglist, args.limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
