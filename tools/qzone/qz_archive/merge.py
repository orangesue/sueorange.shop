"""合并两个通道的结果，并标注哪些说说是从互动记录里找回的。"""

from __future__ import annotations

import hashlib
import re
from typing import Any

WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    return WHITESPACE.sub("", value or "").strip().lower()


def fallback_id(post: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        f"{post.get('createdAt', '')}|{normalize_text(post.get('text', ''))}".encode("utf-8")
    ).hexdigest()
    return f"f{digest[:12]}"


def _merge_images(left: list[str], right: list[str]) -> list[str]:
    merged = list(left)
    for item in right:
        if item not in merged:
            merged.append(item)
    return merged


def _merge_comments(left: list[dict], right: list[dict]) -> list[dict]:
    merged = list(left)
    seen = {(comment.get("author", ""), normalize_text(comment.get("text", ""))) for comment in merged}
    for comment in right:
        key = (comment.get("author", ""), normalize_text(comment.get("text", "")))
        if key in seen:
            continue
        seen.add(key)
        merged.append(comment)
    return merged


def _absorb(target: dict[str, Any], extra: dict[str, Any], *, mark_both: bool) -> dict[str, Any]:
    """把两个通道里同一条说说合并成一条。

    mark_both 只在「现存说说」与「互动记录」两条通道相遇时为真；
    互动记录内部重复的同一条内容只做去重，不改变来源标记。
    """
    target["images"] = _merge_images(target.get("images", []), extra.get("images", []))
    target["comments"] = _merge_comments(target.get("comments", []), extra.get("comments", []))
    target["likes"] = max(int(target.get("likes", 0)), int(extra.get("likes", 0)))
    if mark_both:
        target["source"] = "both"
    if not target.get("text") and extra.get("text"):
        target["text"] = extra["text"]
    if not target.get("createdAt") and extra.get("createdAt"):
        target["createdAt"] = extra["createdAt"]
    if not target.get("repost") and extra.get("repost"):
        target["repost"] = extra["repost"]
    return target


def merge_posts(
    msglist_posts: list[dict[str, Any]],
    feed_posts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """合并规则：

    1. 现存的说说以「未删除说说接口」为准，保留完整正文、评论和配图。
    2. 互动消息列表里能对上 tid 或「时间 + 正文」的，视为同一条，标记 source=both。
    3. 只出现在互动消息列表里的，说明原说说已删除，标记 deleted=True —— 这就是「找回」。
    """
    merged: list[dict[str, Any]] = []
    by_tid: dict[str, dict[str, Any]] = {}
    by_fingerprint: dict[tuple[str, str], dict[str, Any]] = {}

    for post in msglist_posts:
        item = dict(post)
        item["deleted"] = False
        item["source"] = "msglist"
        item["id"] = item.get("tid") or fallback_id(item)
        merged.append(item)
        if item.get("tid"):
            by_tid[item["tid"]] = item
        by_fingerprint[(item.get("createdAt", ""), normalize_text(item.get("text", "")))] = item

    for post in feed_posts:
        item = dict(post)
        item["images"] = list(item.get("images", []))
        item["comments"] = list(item.get("comments", []))

        if not item.get("text") and not item.get("images"):
            continue

        fingerprint = (item.get("createdAt", ""), normalize_text(item.get("text", "")))
        existing = by_tid.get(item.get("tid", "")) or by_fingerprint.get(fingerprint)

        if existing is not None:
            _absorb(existing, item, mark_both=existing.get("source") == "msglist")
            continue

        item["deleted"] = True
        item["source"] = "feeds"
        item["id"] = item.get("tid") or fallback_id(item)
        merged.append(item)
        if item.get("tid"):
            by_tid[item["tid"]] = item
        if fingerprint[1]:
            by_fingerprint[fingerprint] = item

    return merged
