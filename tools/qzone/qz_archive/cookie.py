"""Cookie 解析与 QZone 鉴权参数计算。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class CookieError(ValueError):
    """Cookie 缺失或格式不对。"""


@dataclass(frozen=True)
class Credentials:
    raw_cookie: str
    cookies: dict[str, str]
    uin: str
    skey: str
    p_skey: str
    gtk: int


def parse_cookie_string(raw: str) -> dict[str, str]:
    """把 "a=1; b=2" 解析成字典，忽略空片段和没有等号的部分。"""
    cookies: dict[str, str] = {}
    for chunk in raw.replace("\n", ";").split(";"):
        item = chunk.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key:
            cookies[key] = value.strip()
    return cookies


def strip_login_prefix(value: str) -> str:
    """QZone 的 uin 常写成 o12345678 这种带前缀的形式，真正的号码要剥掉首字母。"""
    text = value.strip()
    if len(text) > 1 and text[0] in "oO" and text[1:].isdigit():
        return text[1:]
    return text


def compute_gtk(skey: str) -> int:
    """QZone 的 g_tk：对 skey 做 DJB 变种哈希后取低 31 位。"""
    if not skey:
        raise CookieError("skey 为空，无法计算 g_tk")

    acc = 5381
    for char in skey:
        acc += (acc << 5) + ord(char)
    return acc & 0x7FFFFFFF


def parse_cookie(raw: str) -> Credentials:
    raw = raw.strip()
    if not raw:
        raise CookieError("Cookie 内容为空")

    cookies = parse_cookie_string(raw)
    if not cookies:
        raise CookieError("Cookie 里没解析出任何键值对")

    uin_source = cookies.get("p_uin") or cookies.get("uin") or cookies.get("ptui_loginuin") or ""
    uin = strip_login_prefix(uin_source)
    skey = cookies.get("skey", "")
    p_skey = cookies.get("p_skey", "")

    missing = [
        name
        for name, value in (("uin/p_uin", uin), ("skey", skey), ("p_skey", p_skey))
        if not value
    ]
    if missing:
        raise CookieError(
            "Cookie 缺少必需字段：" + "、".join(missing) + "。请重新从浏览器完整复制一次。"
        )

    return Credentials(
        raw_cookie=raw,
        cookies=cookies,
        uin=uin,
        skey=skey,
        p_skey=p_skey,
        gtk=compute_gtk(skey),
    )


def read_cookie_file(path: Path) -> Credentials:
    if not path.exists():
        raise CookieError(
            f"找不到 Cookie 文件：{path}\n"
            "请参考 tools/qzone/cookie.example.txt，把浏览器里的 Cookie 存到 "
            "secrets/cookie.txt。"
        )

    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise CookieError(f"{path} 里没有有效内容")

    return parse_cookie("; ".join(lines))

