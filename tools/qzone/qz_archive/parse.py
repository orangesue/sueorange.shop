"""纯解析层：把接口返回的原始文本变成结构化记录。

这一层刻意不碰网络，方便用 fixture 做单元测试；
接口字段一旦变化，通常只需要改这个文件。
"""

from __future__ import annotations

import html as html_module
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from bs4 import BeautifulSoup

CST = timezone(timedelta(hours=8))

JSONP_PATTERN = re.compile(r"^\s*[A-Za-z_$][\w$]*\s*\((.*)\)\s*;?\s*$", re.DOTALL)
TIME_PATTERN = re.compile(
    r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
    r"(?:\s*(\d{1,2})\s*[:：]\s*(\d{2}))?"
)
EMOTICON_PATTERN = re.compile(r"\[em\](e\d+|[\w\u4e00-\u9fff]+)\[/em\]")
MOOD_ID_PATTERN = re.compile(r"mood/([0-9a-zA-Z_-]{6,})")


def decode_bytes(payload: bytes) -> str:
    """QZone 的历史接口在 UTF-8 / GBK 之间摇摆，逐个尝试。"""
    for encoding in ("utf-8", "gb18030", "gbk", "big5"):
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return payload.decode("utf-8", errors="replace")


def strip_jsonp(text: str) -> str:
    """_preloadCallback({...}); -> {...}"""
    match = JSONP_PATTERN.match(text)
    return match.group(1) if match else text


def parse_msglist_jsonp(text: str) -> dict[str, Any]:
    """解析 emotion_cgi_msglist_v6 的返回，失败时返回空结构而不是抛异常。"""
    try:
        payload = json.loads(strip_jsonp(text.strip()))
    except (json.JSONDecodeError, ValueError):
        return {"msglist": [], "total": 0}

    if not isinstance(payload, dict):
        return {"msglist": [], "total": 0}

    msglist = payload.get("msglist")
    if not isinstance(msglist, list):
        msglist = []

    total = payload.get("total")
    if not isinstance(total, int):
        total = len(msglist)

    return {"msglist": msglist, "total": total, "raw": payload}


def clean_html_text(value: Any) -> str:
    """接口里的正文常带 HTML 片段、转义实体和表情占位符。"""
    if value is None:
        return ""

    text = str(value)
    text = EMOTICON_PATTERN.sub("", text)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text("\n")
    text = html_module.unescape(text)
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def unix_to_iso(value: Any) -> str:
    """Unix 秒 -> UTC ISO 字符串；非法值返回空串。"""
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return ""
    if timestamp <= 0:
        return ""
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return ""


def text_time_to_iso(text: str) -> str:
    """把「2020年5月1日 10:30」这类北京时间文本转成 UTC ISO。"""
    match = TIME_PATTERN.search(text or "")
    if not match:
        return ""

    year, month, day, hour, minute = match.groups()
    try:
        moment = datetime(
            int(year),
            int(month),
            int(day),
            int(hour or 0),
            int(minute or 0),
            tzinfo=CST,
        )
    except ValueError:
        return ""

    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_msglist_images(item: dict[str, Any]) -> list[str]:
    """说说配图。pic 里可能是 url1/url2/url3 三档，取最清晰的一档。"""
    images: list[str] = []
    pic = item.get("pic")
    if not isinstance(pic, list):
        return images

    for entry in pic:
        if not isinstance(entry, dict):
            continue
        for key in ("url3", "url2", "url1", "url"):
            value = entry.get(key)
            if isinstance(value, str) and value.startswith("http"):
                images.append(value)
                break

    return images


def extract_msglist_comments(item: dict[str, Any]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    raw_comments = item.get("commentlist")
    if not isinstance(raw_comments, list):
        return comments

    for entry in raw_comments:
        if not isinstance(entry, dict):
            continue
        text = clean_html_text(entry.get("content"))
        if not text:
            continue
        comments.append(
            {
                "author": clean_html_text(entry.get("nickname") or entry.get("name") or "")
                or f"用户{entry.get('uin', '')}",
                "text": text,
                "createdAt": unix_to_iso(entry.get("createTime") or entry.get("create_time")),
            }
        )
    return comments


def extract_likes(item: dict[str, Any]) -> int:
    """v6 接口不一定带赞数，拿不到就是 0。"""
    for key in ("likenum", "like", "praise", "praisenum"):
        value = item.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def msglist_item_to_post(item: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    tid = str(item.get("tid") or item.get("id") or "").strip()
    text = clean_html_text(item.get("content") or item.get("con"))
    created = unix_to_iso(item.get("created_time") or item.get("createdTime"))

    if not tid and not text:
        return None

    repost = ""
    rt_con = item.get("rt_con")
    if isinstance(rt_con, dict):
        repost = clean_html_text(rt_con.get("content"))

    return {
        "id": tid,
        "tid": tid,
        "createdAt": created,
        "text": text,
        "images": extract_msglist_images(item),
        "comments": extract_msglist_comments(item),
        "likes": extract_likes(item),
        "deleted": False,
        "source": "msglist",
        "repost": repost or None,
    }


def parse_msglist_to_posts(text: str) -> list[dict[str, Any]]:
    payload = parse_msglist_jsonp(text)
    posts = []
    for item in payload["msglist"]:
        post = msglist_item_to_post(item)
        if post:
            posts.append(post)
    return posts


def _feed_text(block: Any) -> str:
    """互动消息列表每条的正文位置不稳定，按优先级挑一个像正文的。"""
    for selector in (".f_msg", "._txt", ".txt", ".f_cnt", ".content"):
        node = block.select_one(selector)
        if node:
            text = clean_html_text(node.decode_contents())
            if text:
                return text

    candidates = [clean_html_text(block.get_text("\n"))]
    return max(candidates, key=len, default="")


def _feed_images(block: Any) -> list[str]:
    images: list[str] = []
    for node in block.find_all("img"):
        src = node.get("src") or node.get("data-src") or ""
        if not isinstance(src, str):
            continue
        if not src.startswith("http"):
            continue
        # 头像、图标、表情缩略图都不是我们要的配图
        if any(bad in src for bad in ("qlogo", "avatar", "face", "emotion", "sprite")):
            continue
        if src not in images:
            images.append(src)
    return images


def _feed_tid(block: Any) -> str:
    """互动消息里往往没有显式的 tid，但链接里会带 mood/{tid}。"""
    explicit = str(block.get("data-id") or block.get("data-tid") or "").strip()
    if explicit:
        return explicit

    markup = str(block)
    match = MOOD_ID_PATTERN.search(markup)
    return match.group(1) if match else ""


def parse_feeds_html(text: str) -> list[dict[str, Any]]:
    """解析互动消息列表（feeds2_html_pav_all）的 HTML。

    这里刻意写得宽松：选择器命中失败时退化成「扫描所有 li」，
    以免腾讯换一层 class 名字就直接抓不到。
    """
    soup = BeautifulSoup(text, "html.parser")
    blocks: Iterable[Any] = soup.select("li.f_item") or soup.select("li")

    posts: list[dict[str, Any]] = []
    for block in blocks:
        raw = block.get_text(" ", strip=True)
        created = text_time_to_iso(raw)
        body = _feed_text(block)

        if not created and not body:
            continue

        posts.append(
            {
                "id": "",
                "tid": _feed_tid(block),
                "createdAt": created,
                "text": body,
                "images": _feed_images(block),
                "comments": [],
                "likes": 0,
                "deleted": False,
                "source": "feeds",
                "repost": None,
                "rawText": raw,
            }
        )

    return posts
