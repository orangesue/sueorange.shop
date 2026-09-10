#!/usr/bin/env python3
"""抓取自己的 QQ 空间说说并导出成站点直接可用的 JSON。

用法示例：
    python fetch.py                        # 读 secrets/cookie.txt，抓取全部
    python fetch.py --no-images            # 只抓文字，不下图
    python fetch.py --max-pages 5          # 少翻几页，先试跑
    python fetch.py --dump-raw public/data/raw   # 同时保存原始响应
    python fetch.py --offline-msglist a.txt --offline-feeds b.html

只在本机运行，Cookie 不会被上传到任何地方。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from qz_archive.api import QzoneClient, dump_raw  # noqa: E402
from qz_archive.cookie import CookieError, read_cookie_file  # noqa: E402
from qz_archive.images import localize_post_images  # noqa: E402
from qz_archive.merge import merge_posts  # noqa: E402
from qz_archive.parse import parse_feeds_html, parse_msglist_to_posts  # noqa: E402

DEFAULT_COOKIE = ROOT / "secrets" / "cookie.txt"
DEFAULT_OUT = ROOT / "public" / "data" / "shuoshuo.json"
DEFAULT_IMAGES = ROOT / "public" / "data" / "images"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓取自己的 QQ 空间说说（含从互动记录里找回的已删除内容）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--no-images", action="store_true", help="不下载配图，只保留原始链接")
    parser.add_argument("--max-pages", type=int, default=60, help="未删除说说最多翻几页")
    parser.add_argument("--max-feed-pages", type=int, default=40, help="互动消息最多翻几页")
    parser.add_argument("--dump-raw", type=Path, default=None, help="保存原始响应以便排查")
    parser.add_argument(
        "--offline-msglist",
        type=Path,
        default=None,
        help="离线模式：直接解析本地保存的说说接口响应",
    )
    parser.add_argument(
        "--offline-feeds",
        type=Path,
        default=None,
        help="离线模式：直接解析本地保存的互动消息响应",
    )
    return parser


def load_offline(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def collect(
    args: argparse.Namespace,
) -> tuple[list[dict], list[dict], str | None, QzoneClient | None]:
    """返回 (说说列表, 互动列表, uin, 已登录的客户端)。离线模式没有客户端。"""
    if args.offline_msglist or args.offline_feeds:
        msglist_posts = parse_msglist_to_posts(load_offline(args.offline_msglist))
        feed_posts = parse_feeds_html(load_offline(args.offline_feeds))
        print(f"[离线] 未删除说说 {len(msglist_posts)} 条，互动记录 {len(feed_posts)} 条")
        return msglist_posts, feed_posts, None, None

    credentials = read_cookie_file(args.cookie_file)
    print(f"[登录] 已读取 Cookie，uin={credentials.uin}")

    client = QzoneClient(credentials)

    print(f"[抓取] 未删除说说（最多 {args.max_pages} 页）…")
    msglist_posts, msglist_raw = client.crawl_msglist(max_pages=args.max_pages)
    print(f"[抓取] 未删除说说 {len(msglist_posts)} 条")

    print(f"[抓取] 互动消息列表（最多 {args.max_feed_pages} 页）…")
    feed_posts, feeds_raw = client.crawl_feeds(max_pages=args.max_feed_pages)
    print(f"[抓取] 互动记录 {len(feed_posts)} 条")

    if args.dump_raw:
        dump_raw(args.dump_raw, "msglist", msglist_raw)
        dump_raw(args.dump_raw, "feeds", feeds_raw)
        print(f"[调试] 原始响应已保存到 {args.dump_raw}")

    return msglist_posts, feed_posts, credentials.uin, client


def finalize(posts: list[dict]) -> list[dict]:
    cleaned = []
    for post in posts:
        if not post.get("text") and not post.get("images"):
            continue
        post["comments"] = post.get("comments") or []
        post["images"] = post.get("images") or []
        post["likes"] = int(post.get("likes") or 0)
        post["deleted"] = bool(post.get("deleted"))
        post.pop("rawText", None)
        cleaned.append(post)

    cleaned.sort(key=lambda item: item.get("createdAt") or "", reverse=True)
    return cleaned


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        msglist_posts, feed_posts, uin, client = collect(args)
    except CookieError as error:
        print(f"[错误] {error}", file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 - 给用户一句人话比堆栈有用
        print(f"[错误] 抓取失败：{error}", file=sys.stderr)
        return 1

    posts = finalize(merge_posts(msglist_posts, feed_posts))
    recovered = sum(1 for post in posts if post["deleted"])
    print(f"[合并] 共 {len(posts)} 条，其中从互动记录找回的已删除内容 {recovered} 条")

    if not args.no_images and client is not None:
        pending = sum(len(post["images"]) for post in posts if post["images"])
        print(f"[图片] 待处理 {pending} 张…")
        for post in posts:
            if post["images"]:
                localize_post_images(
                    client.session,
                    post,
                    args.images_dir,
                    referer=f"https://user.qzone.qq.com/{uin}",
                )

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "posts": posts,
    }
    if uin:
        payload["uin"] = uin

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] 已写入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
