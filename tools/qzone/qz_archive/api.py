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
from .parse import decode_bytes, parse_feeds_html, parse_msglist_to_posts

QZONE_BASE = "https://user.qzone.qq.com"

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
    pause: float = 0.8
    msglist_url: str = QZONE_BASE + MSGLIST_PATH
    feeds_url: str = QZONE_BASE + FEEDS_PATH
    session: requests.Session = field(init=False)

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
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        text = decode_bytes(response.content)

        # 登录失效时腾讯会返回登录页而不是数据，早点报出来比默默抓空好
        if "login" in response.url and "qzone" not in text[:2000]:
            raise RuntimeError("登录状态已失效，请重新复制 Cookie")

        return text

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

    def fetch_feeds_page(self, begin_time: int, end_time: int) -> str:
        params = {
            "uin": self.credentials.uin,
            "begin_time": begin_time,
            "end_time": end_time,
            "getappnotification": 1,
            "getnotifi": 1,
            "hasunreadnotice": 1,
            "type": "all",
            "refer": "msg",
            "g_tk": self.credentials.gtk,
        }
        return self._get_text(self.feeds_url, params)

    def crawl_msglist(self, *, max_pages: int = 60, page_size: int = 20) -> tuple[list[dict], list[str]]:
        """翻完未删除说说，返回 (记录列表, 原始响应列表)。"""
        posts: list[dict] = []
        raw_pages: list[str] = []

        for text in self.iter_msglist(max_pages=max_pages, page_size=page_size):
            raw_pages.append(text)
            page_posts = parse_msglist_to_posts(text)
            if not page_posts:
                break
            posts.extend(page_posts)
            if len(page_posts) < page_size:
                break

        return posts, raw_pages

    def crawl_feeds(self, *, max_pages: int = 40) -> tuple[list[dict], list[str]]:
        """沿时间轴往前翻互动消息，返回 (记录列表, 原始响应列表)。"""
        posts: list[dict] = []
        raw_pages: list[str] = []
        begin_time = int(time.time())
        end_time = 0
        seen_keys: set[tuple[str, str]] = set()

        for _ in range(max_pages):
            text = self.fetch_feeds_page(begin_time, end_time)
            raw_pages.append(text)
            page_posts = parse_feeds_html(text)

            fresh = []
            for post in page_posts:
                key = (post.get("createdAt", ""), post.get("text", "")[:80])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                fresh.append(post)

            if not fresh:
                break

            posts.extend(fresh)

            earliest = min(
                (post["createdAt"] for post in fresh if post.get("createdAt")),
                default="",
            )
            if not earliest:
                break

            begin_time = _iso_to_unix(earliest) - 1
            if begin_time <= 0:
                break
            time.sleep(self.pause)

        return posts, raw_pages


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

