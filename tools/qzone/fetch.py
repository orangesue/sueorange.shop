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
from qz_archive.parse import (  # noqa: E402
    parse_feed_items,
    parse_feeds_html,
    parse_feeds_payload,
    parse_msglist_to_posts,
)

DEFAULT_COOKIE = ROOT / "secrets" / "cookie.txt"
DEFAULT_OUT = ROOT / "public" / "data" / "shuoshuo.json"
DEFAULT_IMAGES = ROOT / "public" / "data" / "images"
DEFAULT_PROGRESS = ROOT / "public" / "data" / ".fetch-progress.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓取自己的 QQ 空间说说（含从互动记录里找回的已删除内容）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--no-images", action="store_true", help="不下载配图，只保留原始链接")
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="不联网抓说说，只把已导出 JSON 里的配图下载到本地",
    )
    parser.add_argument(
        "--feeds-only",
        action="store_true",
        help="只爬互动记录，从已有说说里比对出已删除内容并写回",
    )
    parser.add_argument("--max-pages", type=int, default=60, help="未删除说说最多翻几页")
    parser.add_argument("--page-size", type=int, default=20, help="每页抓多少条（默认 20）")
    parser.add_argument("--pause", type=float, default=1.2, help="每页之间的间隔秒数，太小容易触发限流")
    parser.add_argument("--max-feed-pages", type=int, default=40, help="互动消息最多翻几页")
    parser.add_argument("--fresh", action="store_true", help="忽略断点，从头抓")
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=DEFAULT_PROGRESS,
        help="断点文件位置（.gitignore 已排除）",
    )
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


def read_json_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def merge_unique(*groups: list[dict]) -> list[dict]:
    """按 tid（没有则按时间+正文）去重合并，保留先出现的。"""
    merged: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for post in group:
            key = str(post.get("tid") or f"{post.get('createdAt')}|{post.get('text', '')[:40]}")
            if key in seen:
                continue
            seen.add(key)
            merged.append(post)
    return merged


def write_output(path: Path, posts: list[dict], uin: str | None, partial: bool) -> None:
    posts = sorted(
        (post for post in posts if post.get("text") or post.get("images")),
        key=lambda item: item.get("createdAt") or "",
        reverse=True,
    )
    payload: dict = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "posts": posts,
    }
    if uin:
        payload["uin"] = uin
    if partial:
        payload["partial"] = True

    path.parent.mkdir(parents=True, exist_ok=True)
    # 先写临时文件再改名，避免中途失败留下半个 JSON
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def collect(
    args: argparse.Namespace,
) -> tuple[list[dict], list[dict], str | None, QzoneClient | None, bool]:
    """返回 (说说列表, 互动列表, uin, 客户端, 是否被限流中断)。"""
    if args.feeds_only:
        credentials = read_cookie_file(args.cookie_file)
        base_posts = read_json_file(args.out).get("posts") or []
        client = QzoneClient(credentials, pause=args.pause)
        print(f"[恢复] 已有 {len(base_posts)} 条说说，开始沿时间轴爬互动记录…")

        # 逐页落盘：既能看到进度，中途被打断也不会白跑
        records: list[dict] = []

        def on_feed_page(page_posts: list[dict], page_index: int, earliest: str) -> None:
            records[:] = page_posts
            recovered = merge_recovered(base_posts, records)
            write_output(
                args.out,
                finalize(merge_posts(base_posts, []) + recovered),
                credentials.uin,
                partial=True,
            )
            print(
                f"    第 {page_index:>3} 页：互动记录 {len(records):>5} 条，"
                f"判定已找回 {len(recovered):>4} 条，最早到 {(earliest or '')[:10]}",
                flush=True,
            )

        feed_posts, feeds_raw, _ = client.crawl_feeds(
            max_pages=args.max_feed_pages,
            page_size=args.page_size,
            on_page=on_feed_page,
        )
        print(f"[恢复] 互动记录 {len(feed_posts)} 条")
        if args.dump_raw:
            dump_raw(args.dump_raw, "feeds", feeds_raw)
        return base_posts, feed_posts, credentials.uin, client, bool(client.last_error)

    if args.images_only:
        credentials = read_cookie_file(args.cookie_file)
        posts = read_json_file(args.out).get("posts") or []
        if not posts:
            print(f"[错误] {args.out} 里还没有说说，请先跑一次正常抓取。", file=sys.stderr)
            return [], [], credentials.uin, None, True
        print(f"[图片模式] 读取已有 {len(posts)} 条说说，只下载配图")
        return posts, [], credentials.uin, QzoneClient(credentials, pause=args.pause), False

    if args.offline_msglist or args.offline_feeds:
        msglist_posts = parse_msglist_to_posts(load_offline(args.offline_msglist))
        raw_feeds = load_offline(args.offline_feeds)
        feed_posts = parse_feed_items(parse_feeds_payload(raw_feeds), None)
        if not feed_posts:
            feed_posts = parse_feeds_html(raw_feeds)
        print(f"[离线] 未删除说说 {len(msglist_posts)} 条，互动记录 {len(feed_posts)} 条")
        return msglist_posts, feed_posts, None, None, False

    credentials = read_cookie_file(args.cookie_file)
    print(f"[登录] 已读取 Cookie，uin={credentials.uin}")

    client = QzoneClient(credentials, pause=args.pause)

    existing: list[dict] = []
    start_pos = 0
    if not args.fresh:
        info = read_json_file(args.progress_file)
        if info.get("uin") == credentials.uin and info.get("next_pos"):
            start_pos = int(info["next_pos"])
            existing = read_json_file(args.out).get("posts") or []
            print(
                f"[续传] 本地已有 {len(existing)} 条，从 pos={start_pos} 继续。"
                "（想从头抓加 --fresh）"
            )

    saved: list[dict] = merge_unique(existing)

    def on_page(page_posts: list[dict], next_pos: int) -> None:
        # 每抓完一页就落盘：中途被限流也不会前功尽弃
        saved[:] = merge_unique(page_posts, existing)
        write_output(args.out, saved, credentials.uin, partial=True)
        args.progress_file.parent.mkdir(parents=True, exist_ok=True)
        args.progress_file.write_text(
            json.dumps({"uin": credentials.uin, "next_pos": next_pos}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"    …累计 {len(saved)} 条（下一页 pos={next_pos}）", flush=True)

    print(f"[抓取] 未删除说说（从 pos={start_pos} 开始，最多 {args.max_pages} 页）…")
    msglist_posts, msglist_raw, _next_pos = client.crawl_msglist(
        max_pages=args.max_pages,
        page_size=args.page_size,
        start_pos=start_pos,
        on_page=on_page,
    )

    if client.last_error:
        print(f"[限流] {client.last_error}")
        print(f"[提示] 本次结果已保存（{len(saved)} 条）。等几分钟后重跑同一条命令会自动续传。")
        return saved, [], credentials.uin, None, True

    all_posts = merge_unique(msglist_posts, existing)
    print(f"[抓取] 未删除说说：本次新增 {len(msglist_posts)} 条，合计 {len(all_posts)} 条")

    feed_posts: list[dict] = []
    feeds_raw: list[str] = []
    if args.max_feed_pages > 0:
        print(f"[抓取] 互动消息列表（最多 {args.max_feed_pages} 页）…")
        feed_posts, feeds_raw, _ = client.crawl_feeds(
            max_pages=args.max_feed_pages, page_size=args.page_size
        )
        print(f"[抓取] 互动记录 {len(feed_posts)} 条")

    if args.dump_raw:
        dump_raw(args.dump_raw, "msglist", msglist_raw)
        dump_raw(args.dump_raw, "feeds", feeds_raw)
        print(f"[调试] 原始响应已保存到 {args.dump_raw}")

    return all_posts, feed_posts, credentials.uin, client, False


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


def _normalized_text(text: str | None) -> str:
    return "".join((text or "").split()).lower()


def merge_recovered(existing_posts: list[dict], feed_records: list[dict]) -> list[dict]:
    """把互动记录里能对上正文的「已删除说说」挑出来。

    规则：互动记录带的是原说说正文（可能被截断）。凡是正文能跟现存说说
    前缀对上的，说明它没被删，跳过；对不上的，就是已经删掉、只能从
    互动痕迹里还原的那批。
    """
    existing = {
        _normalized_text(post.get("text"))
        for post in existing_posts
        if post.get("text")
    }
    seen: set[str] = set()
    recovered: list[dict] = []

    for record in feed_records:
        text = _normalized_text(record.get("text"))
        if not text or text in seen:
            continue
        seen.add(text)

        prefix = text[:24]
        matched = any(
            candidate.startswith(prefix) or text.startswith(candidate[:24])
            for candidate in existing
            if candidate
        )
        if matched:
            continue

        item = dict(record)
        item["deleted"] = True
        item["source"] = "feeds"
        recovered.append(item)

    return recovered


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        msglist_posts, feed_posts, uin, client, aborted = collect(args)
    except CookieError as error:
        print(f"[错误] {error}", file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 - 给用户一句人话比堆栈有用
        print(f"[错误] 抓取失败：{error}", file=sys.stderr)
        return 1

    base_posts = finalize(merge_posts(msglist_posts, []))
    recovered = merge_recovered(base_posts, feed_posts)
    posts = finalize(base_posts + recovered)
    recovered_count = sum(1 for post in posts if post["deleted"])
    print(f"[合并] 共 {len(posts)} 条，其中从互动记录找回的已删除内容 {recovered_count} 条")

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
        # 图片下载会改写 images 字段，落盘一次保证本地路径被保存
        write_output(args.out, posts, uin, partial=False)

    write_output(args.out, posts, uin, partial=aborted)

    if aborted:
        print(
            f"[未完成] 抓取被限流中断，已保存 {len(posts)} 条。"
            "过几分钟重跑同一条命令会自动续传。"
        )
        return 3

    # 完整跑完后清掉断点，下次就是全新一轮
    args.progress_file.unlink(missing_ok=True)
    print(f"[完成] 已写入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
