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

try:  # 解析互动消息返回的 JS 对象字面量（键不带引号、值用单引号）
    import json5
except ImportError:  # pragma: no cover - 缺依赖时退化成正则兜底
    json5 = None  # type: ignore[assignment]

CST = timezone(timedelta(hours=8))

CALLBACK_PATTERN = re.compile(r"^\s*[A-Za-z_$][\w$]*\s*\((.*)\)\s*;?\s*$", re.DOTALL)
# 腾讯返回的是 JS 对象字面量，里面会出现 undefined 这类 JSON5 也不认的值
UNDEFINED_VALUE_PATTERN = re.compile(r"([:,\[])\s*undefined\b")
NAN_VALUE_PATTERN = re.compile(r"([:,\[])\s*NaN\b")
HTML_LITERAL_PATTERN = re.compile(r"html\s*:\s*'((?:[^'\\]|\\.)*)'")
ABSTIME_LITERAL_PATTERN = re.compile(r"abstime\s*:\s*'(\d+)'")
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


def strip_callback(text: str) -> str:
    """_preloadCallback({...}); / _Callback({...}) -> {...}"""
    stripped = text.strip()
    match = CALLBACK_PATTERN.match(stripped)
    return match.group(1) if match else stripped


# 早期版本用的名字，保留以免外部调用断掉
strip_jsonp = strip_callback


def parse_feeds_payload(text: str) -> dict[str, Any]:
    """互动消息接口返回的是 `_Callback({...})`，里面是 JS 对象字面量而非合法 JSON。

    优先用 json5 正确解析；失败时退化成「把所有 html 字段抠出来」，
    至少不会一条都拿不到。
    """
    inner = strip_callback(text)

    if json5 is not None:
        try:
            normalized = UNDEFINED_VALUE_PATTERN.sub(r"\1 null", inner)
            normalized = NAN_VALUE_PATTERN.sub(r"\1 null", normalized)
            payload = json5.loads(normalized)
            if isinstance(payload, dict):
                return payload
        except Exception as error:  # noqa: BLE001 - 任何解析失败都走兜底
            LAST_JSON5_ERROR[0] = str(error)

    return _feeds_regex_fallback(inner)


# 上一次 json5 解析失败的原因，排查接口变化时很有用
LAST_JSON5_ERROR: list[str] = [""]

JS_SIMPLE_ESCAPES = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "b": "\b",
    "f": "\f",
    "/": "/",
    "'": "'",
    '"': '"',
    "\\": "\\",
    "0": "\0",
}


def unescape_js_string(text: str) -> str:
    """还原 JS 字符串字面量里的转义：\\x3C -> <、\\/ -> /、\\u4e2d -> 中。"""
    out: list[str] = []
    index = 0
    length = len(text)

    while index < length:
        char = text[index]
        if char != "\\" or index + 1 >= length:
            out.append(char)
            index += 1
            continue

        marker = text[index + 1]

        if marker == "x" and index + 3 < length:
            try:
                out.append(chr(int(text[index + 2 : index + 4], 16)))
                index += 4
                continue
            except ValueError:
                pass

        if marker == "u" and index + 5 < length:
            try:
                out.append(chr(int(text[index + 2 : index + 6], 16)))
                index += 6
                continue
            except ValueError:
                pass

        out.append(JS_SIMPLE_ESCAPES.get(marker, marker))
        index += 2

    return "".join(out)


def _feeds_regex_fallback(inner: str) -> dict[str, Any]:
    """兜底解析：直接抠 html / abstime 字面量，凑成和正常结构一样的形状。"""
    items: list[dict[str, Any]] = []
    timestamps = ABSTIME_LITERAL_PATTERN.findall(inner)

    for index, match in enumerate(HTML_LITERAL_PATTERN.finditer(inner)):
        markup = unescape_js_string(match.group(1))
        items.append(
            {
                "html": markup,
                "abstime": timestamps[index] if index < len(timestamps) else "",
                "_fallback": True,
            }
        )

    return {"data": {"main": {"_fallback": True}, "data": items}}


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


# ---------- 统一时间线（format=json 的互动记录） ----------

FEED_CONTENT_SELECTORS = (
    "p.txt-box-title",
    "h4.f-title",
    "div.txt-prewrap",
    "div.f-info-content",
    "div.f-info",
    "div.f-single-content",
    "div.f_msg",
)

DELETED_MARKERS = (
    "已删除",
    "被删除",
    "已不存在",
    "已失效",
    "无权查看",
    "不可访问",
    "暂不支持查看",
    "内容暂不支持",
)

OBJECT_ID_PATTERNS = (
    re.compile(r"(?:tid|curkey|unikey|topicId)=([A-Za-z0-9_\-]+)"),
    re.compile(r"/mood/([A-Za-z0-9_\-]+)"),
    re.compile(r"blogid=(\d+)"),
)


def extract_object_id(markup: str) -> str:
    for pattern in OBJECT_ID_PATTERNS:
        match = pattern.search(markup)
        if match:
            return match.group(1)
    return ""


def strip_author_prefix(text: str, author: str) -> str:
    if not author:
        return text
    # 作者名和冒号之间可能有空格，比如「橘子 ： 正文」
    pattern = re.compile(rf"^\s*{re.escape(author)}\s*[：:]\s*")
    return pattern.sub("", text, count=1).strip()


def extract_author_uin(soup: Any) -> str:
    """互动记录里 a.nickname 才是说说作者，拿它的 QQ 号。"""
    node = soup.select_one("a.nickname")
    if node is None:
        return ""

    link = node.get("link") or ""
    if link.startswith("nameCard_"):
        return link[len("nameCard_") :]

    href = node.get("href") or ""
    match = re.search(r"user\.qzone\.qq\.com/(\d+)", href)
    return match.group(1) if match else ""


PLACEHOLDER_MARKERS = ("功能内测中", "内容暂不支持查看", "暂不支持查看")


def parse_feed_item(item: dict[str, Any], self_uin: str) -> dict[str, Any] | None:
    """把统一时间线里的一条互动记录（JSON 格式）转成站点记录。"""
    markup = item.get("html") or ""
    if not markup:
        return None

    soup = BeautifulSoup(markup, "html.parser")

    author_node = soup.select_one("a.nickname")
    author = clean_html_text(author_node.get_text(" ", strip=True)) if author_node else ""
    author_uin = extract_author_uin(soup)

    # 关键过滤：互动流里混着好友的动态/评论，只有「作者是我」的才算我的说说
    if author_uin and str(author_uin) != str(self_uin):
        return None

    state_node = soup.select_one("span.state")
    state = clean_html_text(state_node.get_text(" ", strip=True)) if state_node else ""

    text = ""
    for selector in FEED_CONTENT_SELECTORS:
        node = soup.select_one(selector)
        candidate = clean_html_text(node.get_text(" ", strip=True)) if node else ""
        if candidate:
            text = candidate
            break

    text = strip_author_prefix(text, author)

    # 原说说已被腾讯清空、只剩占位提示的，正文留空，让页面显示「只剩互动痕迹」
    if any(marker in text for marker in PLACEHOLDER_MARKERS):
        text = ""

    images: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not isinstance(src, str) or not src.startswith("http"):
            continue
        if any(bad in src for bad in ("qlogo", "avatar", "face", "emotion", "sprite", "/ac/")):
            continue
        if src not in images:
            images.append(src)

    created = unix_to_iso(item.get("abstime"))
    if not text and not images and not created:
        return None

    tid = str(item.get("key") or extract_object_id(markup) or "").strip()
    deleted = any(marker in (state + " " + text) for marker in DELETED_MARKERS)

    return {
        "id": tid,
        "tid": tid,
        "createdAt": created,
        "text": text,
        "images": images,
        "comments": [],
        "likes": 0,
        "deleted": deleted,
        "source": "feeds",
        "repost": None,
        "state": state,
        "author": author,
        "authorUin": author_uin,
    }


def parse_feed_items(payload: dict[str, Any], self_uin: str) -> list[dict[str, Any]]:
    outer = payload.get("data") or {}
    items = outer.get("data") or []
    posts: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        post = parse_feed_item(item, self_uin)
        if post:
            posts.append(post)
    return posts
