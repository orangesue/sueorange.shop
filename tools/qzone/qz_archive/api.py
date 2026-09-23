"""QZone 网络层：只负责发请求、翻页、返回原始文本。

接口地址和参数集中在这里，腾讯一旦调整，改这一个文件就够。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import requests

from .cookie import Credentials
from .parse import (
    decode_bytes,
    parse_feed_items,
    parse_feeds_payload,
    parse_msglist_to_posts,
)

QZONE_BASE = "https://user.qzone.qq.com"

# 腾讯偶尔会用这些状态码限流，重试通常能过去
RETRY_STATUS = {429, 500, 501, 502, 503, 504}

# 未删除的说说
MSGLIST_PATH = "/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6"
# 互动消息列表（含已被删除、但仍留有互动痕迹的内容）
FEEDS_PATH = "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds2_html_pav_all"

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class QzoneClient:
    credentials: Credentials
    timeout: int = 20
    pause: float = 3.0
    retries: int = 4
    # 被限流（501）时宁可等久一点：试探发现秒级重试完全无效，反而会延长封禁
    backoff: float = 60.0
    msglist_url: str = QZONE_BASE + MSGLIST_PATH
    feeds_url: str = QZONE_BASE + FEEDS_PATH
    session: requests.Session = field(init=False)
    last_error: str = ""

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DESKTOP_UA,
                "Referer": f"{QZONE_BASE}/{self.credentials.uin}",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cookie": self.credentials.raw_cookie,
            }
        )

    # ---------- 底层请求 ----------

    def _get_text(self, url: str, params: dict[str, Any]) -> str:
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as error:
                last_error = error
            else:
                if response.status_code in RETRY_STATUS:
                    last_error = RuntimeError(
                        f"{response.status_code} {response.reason}（多半是限流）"
                    )
                else:
                    response.raise_for_status()
                    text = decode_bytes(response.content)
                    # 登录失效时腾讯会返回登录页而不是数据
                    if "login" in response.url and "qzone" not in text[:2000]:
                        raise RuntimeError("登录状态已失效，请重新复制 Cookie")
                    return text

            if attempt < self.retries:
                wait = self.backoff * attempt
                print(f"    [重试 {attempt}/{self.retries - 1}] {last_error}，{wait:.0f} 秒后再试")
                time.sleep(wait)

        raise RuntimeError(f"连续 {self.retries} 次请求都失败：{last_error}")

    # ---------- 通道一：未删除说说 ----------

    def fetch_msglist_page(self, pos: int, num: int = 20) -> str:
        params = {
            "uin": self.credentials.uin,
            "ftype": 0,
            "sort": 0,
            "pos": pos,
            "num": num,
            "replynum": 100,
            "g_tk": self.credentials.gtk,
            "callback": "_preloadCallback",
            "code_version": 1,
            "format": "jsonp",
            "need_private_comment": 1,
        }
        return self._get_text(self.msglist_url, params)

    def iter_msglist(self, *, max_pages: int = 60, page_size: int = 20) -> Iterator[str]:
        for page in range(max_pages):
            yield self.fetch_msglist_page(pos=page * page_size, num=page_size)
            time.sleep(self.pause)

    # ---------- 通道二：互动消息列表 ----------

    def fetch_feeds_page(self, offset: int, count: int = 30) -> str:
        """统一时间线：含互动记录、以及已删除/不可见内容的占位。"""
        params = {
            "uin": self.credentials.uin,
            "begin_time": "0",
            "end_time": "0",
            "getappnotification": 1,
            "getnotifi": 1,
            "has_get_key": 0,
            "offset": offset,
            "set": 0,
            "count": count,
            "useutf8": 1,
            "outputhtmlfeed": 1,
            "scope": 1,
            "format": "json",
            "g_tk": self.credentials.gtk,
        }
        return self._get_text(self.feeds_url, params)

    def crawl_msglist(
        self,
        *,
        max_pages: int = 60,
        page_size: int = 20,
        start_pos: int = 0,
        on_page: Any = None,
    ) -> tuple[list[dict], list[str], int]:
        """翻未删除说说，返回 (记录列表, 原始响应列表, 下一页 pos)。

        on_page(page_posts, next_pos) 每抓完一页回调一次，用于落盘，避免被限流后全军覆没。
        """
        posts: list[dict] = []
        raw_pages: list[str] = []
        pos = start_pos

        for _ in range(max_pages):
            try:
                text = self.fetch_msglist_page(pos=pos, num=page_size)
            except RuntimeError as error:
                # 中途被限流时不要把已经抓到的丢掉，交给调用方决定怎么办
                self.last_error = str(error)
                break
            raw_pages.append(text)
            page_posts = parse_msglist_to_posts(text)
            if not page_posts:
                break
            posts.extend(page_posts)
            pos += page_size
            if on_page is not None:
                on_page(list(posts), pos)
            if len(page_posts) < page_size:
                break
            time.sleep(self.pause)

        return posts, raw_pages, pos

    def crawl_feeds(
        self,
        *,
        max_pages: int = 120,
        page_size: int = 30,
        on_page: Any = None,
    ) -> tuple[list[dict], list[str], int]:
        """沿时间轴往前翻互动消息，返回 (记录列表, 原始响应列表, 下一页 offset)。

        on_page(page_posts, 页码, 本页最早时间) 每抓完一页回调一次，便于边跑边落盘。
        """
        posts: list[dict] = []
        raw_pages: list[str] = []
        seen_keys: set[str] = set()

        for page in range(max_pages):
            text = ""
            payload: dict[str, Any] = {}
            for attempt in range(self.retries + 1):
                text = self.fetch_feeds_page(offset=page * page_size, count=page_size)
                payload = parse_feeds_payload(text)
                code = payload.get("code")
                if code in (None, 0):
                    break
                wait = self.backoff * (attempt + 1)
                print(f"    [忙] code={code} {payload.get('message')}，等 {wait:.0f} 秒")
                time.sleep(wait)
            else:
                self.last_error = f"连续 {self.retries + 1} 次 network busy"
                break

            raw_pages.append(text)
            page_posts = parse_feed_items(payload, self.credentials.uin)

            fresh = []
            for post in page_posts:
                key = (post.get("tid", ""), post.get("createdAt", ""), post.get("text", "")[:80])
                key_str = "|".join(key)
                if key_str in seen_keys:
                    continue
                seen_keys.add(key_str)
                fresh.append(post)

            if not fresh:
                break

            posts.extend(fresh)

            if on_page is not None:
                earliest = min(
                    (post.get("createdAt") or "" for post in fresh if post.get("createdAt")),
                    default="",
                )
                on_page(list(posts), page + 1, earliest)

            time.sleep(self.pause)

        return posts, raw_pages, (len(raw_pages) * page_size)


def _iso_to_unix(value: str) -> int:
    from datetime import datetime

    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return 0


def dump_raw(directory: Path, name: str, pages: list[str]) -> None:
    """把原始响应存到本地，方便定位解析问题（目录已被 .gitignore 排除）。"""
    directory.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(pages, start=1):
        target = directory / f"{name}-{index:03d}.txt"
        target.write_text(page, encoding="utf-8")
