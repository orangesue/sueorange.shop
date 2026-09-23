#!/usr/bin/env python3
"""从 QQ空间前端代码里挖接口路径，找出「消息」用的是哪个 cgi。

思路：先抓主页 HTML，再顺着它引用的 JS 去搜 cgi-bin 路径，
按关键词（msg/notice/comment/praise/...）筛出候选，逐个试。
"""

from __future__ import annotations

import re
import sys
import time
from collections import Counter
from urllib.parse import urlencode
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qz_archive.api import DESKTOP_UA, QZONE_BASE  # noqa: E402
from qz_archive.cookie import read_cookie_file  # noqa: E402
from qz_archive.parse import decode_bytes  # noqa: E402

CGI_PATTERN = re.compile(r"[/\w.%-]*cgi-bin[/\w.-]+")
KEYWORDS = ("msg", "notice", "comment", "praise", "like", "interact", "feed", "visit", "mood")


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

    found: Counter[str] = Counter()

    pages = [
        f"{QZONE_BASE}/{credentials.uin}/main",
        f"{QZONE_BASE}/{credentials.uin}",
    ]

    scripts: set[str] = set()

    for url in pages:
        try:
            response = session.get(url, timeout=25)
        except requests.RequestException as error:
            print(f"[页面] {url} 请求失败: {error}")
            continue
        text = decode_bytes(response.content)
        print(f"[页面] {url} -> {response.status_code}，{len(text)} 字符")
        for match in CGI_PATTERN.findall(text):
            found[match] += 1
        soup = BeautifulSoup(text, "html.parser")
        for node in soup.find_all("script"):
            src = node.get("src")
            if isinstance(src, str) and src.startswith("http"):
                scripts.add(src)

    print(f"\n[主页] 发现 {len(scripts)} 个外部脚本，开始扫描…")
    for src in sorted(scripts)[:12]:
        try:
            response = session.get(src, timeout=30)
        except requests.RequestException:
            continue
        body = decode_bytes(response.content)
        hits = [match for match in CGI_PATTERN.findall(body) if any(k in match.lower() for k in KEYWORDS)]
        if hits:
            print(f"  {src.split('/')[-1][:40]}  ->  {len(hits)} 个候选")
            for match in Counter(hits).most_common(8):
                found[match[0]] += match[1]

    print("\n=== 含关键词的候选接口 ===")
    for path, count in found.most_common(40):
        if any(k in path.lower() for k in KEYWORDS):
            print(f"  {count:>3}x  {path}")

    return 0


CANDIDATES = [
    ("ic2 feeds3_html_more", "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds3_html_more"),
    ("ic2 feeds_html_act_all", "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds_html_act_all"),
    ("ic2 cgi_get_feeds_count", "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/cgi_get_feeds_count.cgi"),
    ("taotao emotion_cgi_re_feeds", "/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_re_feeds"),
    ("feeds cgi_rss_out", "/proxy/domain/feeds.qzone.qq.com/cgi-bin/cgi_rss_out"),
]


def try_endpoints() -> int:
    """给每个候选接口发一轮请求，看谁能返回数据、以及里面有没有「我」。"""
    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    base = {
        "uin": credentials.uin,
        "g_tk": credentials.gtk,
        "type": "all",
        "refer": "msg",
        "getappnotification": 1,
        "getnotifi": 1,
        "hasunreadnotice": 1,
    }

    for label, path in CANDIDATES:
        url = QZONE_BASE + path
        try:
            response = session.get(url, params=base, timeout=25)
        except requests.RequestException as error:
            print(f"\n### {label}: 请求异常 {error}")
            continue

        text = decode_bytes(response.content)
        uins = re.findall(r"fct_(\d+)_", text)
        mine = "★★ 含我自己" if credentials.uin in uins else ""
        print(f"\n### {label}  http={response.status_code}  长度={len(text)}  {mine}")
        snippet = " ".join(BeautifulSoup(text, "html.parser").get_text(" ", strip=True).split())
        print(f"    {(snippet[:160] or text[:160])!r}")
        time.sleep(2)

    return 0


FEEDS3_URL = QZONE_BASE + "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds3_html_more"


def probe_feeds3() -> int:
    """feeds3_html_more 支持按时间窗翻页，试试能不能翻到很久以前、并找到我自己。"""
    from datetime import datetime, timezone

    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    now = int(datetime.now(tz=timezone.utc).timestamp())
    variants = [
        ("filter=all applist=all", {"scope": 0, "view": 1, "filter": "all", "applist": "all", "fupdate": 1, "refresh": 0, "begintime": 0, "endtime": 0, "count": 30}),
        ("时间窗 1 天内", {"scope": 0, "view": 1, "filter": "all", "applist": "all", "fupdate": 1, "begintime": now - 86400, "endtime": now, "count": 30}),
        ("时间窗 1~3 年前", {"scope": 0, "view": 1, "filter": "all", "applist": "all", "fupdate": 1, "begintime": now - 1095 * 86400, "endtime": now - 365 * 86400, "count": 30}),
        ("只要我的说说", {"scope": 0, "view": 1, "filter": "mine", "applist": "all", "fupdate": 1, "count": 30}),
    ]

    for label, extra in variants:
        params = {"uin": credentials.uin, "g_tk": credentials.gtk, **extra}
        try:
            response = session.get(FEEDS3_URL, params=params, timeout=25)
        except requests.RequestException as error:
            print(f"\n### {label}: 请求异常 {error}")
            continue

        text = decode_bytes(response.content)
        payload = parse_feeds_payload(text)
        outer = payload.get("data") if isinstance(payload, dict) else None
        items = (outer or {}).get("data") or []

        print(f"\n### {label}  http={response.status_code}  响应={len(text)}  条目={len(items)}")
        print(f"    main={((outer or {}).get('main'))}")
        for index, item in enumerate(items[:3]):
            if isinstance(item, dict):
                markup = item.get("html") or ""
                uins = sorted(set(re.findall(r"fct_(\d+)_", markup)))
                mine = "★我" if credentials.uin in uins else "  "
                preview = " ".join(BeautifulSoup(markup, "html.parser").get_text(" ", strip=True).split())[:80]
                print(f"    #{index} {mine} abstime={item.get('abstime')} uins={uins[:3]} | {preview}")
        time.sleep(2)

    return 0


def self_scan(years: int = 12) -> int:
    """按年扫一遍好友动态，统计其中有多少条是「我自己」发的。"""
    from datetime import datetime, timezone

    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    now = int(datetime.now(tz=timezone.utc).timestamp())
    year = 365 * 86400
    total = 0
    mine_posts: list[str] = []

    for step in range(years):
        begin = now - (step + 1) * year
        end = now - step * year
        params = {
            "uin": credentials.uin,
            "g_tk": credentials.gtk,
            "scope": 0,
            "view": 1,
            "filter": "all",
            "applist": "all",
            "fupdate": 1,
            "refresh": 0,
            "begintime": begin,
            "endtime": end,
            "count": 30,
        }
        try:
            response = session.get(FEEDS3_URL, params=params, timeout=30)
        except requests.RequestException as error:
            print(f"  {step} 年前: 请求异常 {error}")
            continue

        text = decode_bytes(response.content)
        payload = parse_feeds_payload(text)
        items = ((payload.get("data") or {}).get("data") or []) if isinstance(payload, dict) else []
        total += len(items)

        mine = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            markup = item.get("html") or ""
            if credentials.uin in re.findall(r"fct_(\d+)_", markup):
                mine += 1
                preview = " ".join(
                    BeautifulSoup(markup, "html.parser").get_text(" ", strip=True).split()
                )[:80]
                mine_posts.append(f"abstime={item.get('abstime')} {preview}")

        stamp = datetime.fromtimestamp(end, tz=timezone.utc).strftime("%Y-%m")
        print(f"  {stamp} 区间: 条目={len(items):<3} 其中我发的={mine}  响应={len(text)}")
        time.sleep(2)

    print(f"\n合计扫描 {total} 条动态，其中属于我自己的 {len(mine_posts)} 条")
    for entry in mine_posts[:15]:
        print(f"  {entry}")

    return 0


def deep() -> int:
    """把前端脚本全挖一遍，并把计数接口的完整返回打出来。"""
    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    count_url = QZONE_BASE + "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/cgi_get_feeds_count.cgi"
    try:
        response = session.get(count_url, params={"uin": credentials.uin, "g_tk": credentials.gtk}, timeout=25)
        print("=== 计数接口完整返回 ===")
        print(decode_bytes(response.content))
    except requests.RequestException as error:
        print(f"计数接口失败: {error}")

    print("\n=== 扫描全部脚本里的 cgi-bin 路径 ===")
    paths: Counter[str] = Counter()
    scripts: list[str] = []

    for url in (f"{QZONE_BASE}/{credentials.uin}/main", f"{QZONE_BASE}/{credentials.uin}"):
        try:
            text = decode_bytes(session.get(url, timeout=25).content)
        except requests.RequestException:
            continue
        soup = BeautifulSoup(text, "html.parser")
        for node in soup.find_all("script"):
            src = node.get("src")
            if isinstance(src, str) and src.startswith("http"):
                scripts.append(src)

    print(f"共 {len(scripts)} 个脚本")
    for src in scripts:
        try:
            body = decode_bytes(session.get(src, timeout=30).content)
        except requests.RequestException:
            continue
        for match in re.findall(r"cgi-bin[/\w.-]+", body):
            paths[match] += 1

    for path, count in paths.most_common(60):
        mark = "  <<<" if any(
            k in path.lower() for k in ("msg", "notice", "interact", "praise", "comment", "reply", "about")
        ) else ""
        print(f"  {count:>4}x  {path}{mark}")

    return 0


def probe_hostuin() -> int:
    """试试用 hostuin 参数让动态流返回「空间主人自己的说说」。"""
    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    variants = [
        ("feeds3 hostuin=自己", FEEDS3_URL, {"hostuin": credentials.uin, "scope": 1, "view": 1, "filter": "all", "applist": "all", "count": 30}),
        ("feeds3 hostuin + filter=mine", FEEDS3_URL, {"hostuin": credentials.uin, "scope": 1, "filter": "mine", "count": 30}),
        ("feeds3 hostuin + type=all", FEEDS3_URL, {"hostuin": credentials.uin, "type": "all", "refer": "msg", "count": 30}),
        ("feeds3 只按 hostuin", FEEDS3_URL, {"hostuin": credentials.uin, "count": 30}),
        (
            "feeds2 hostuin",
            QZONE_BASE + "/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds2_html_pav_all",
            {"hostuin": credentials.uin, "type": "all", "refer": "msg", "getappnotification": 1, "getnotifi": 1, "hasunreadnotice": 1},
        ),
    ]

    for label, url, extra in variants:
        params = {"uin": credentials.uin, "g_tk": credentials.gtk, **extra}
        try:
            response = session.get(url, params=params, timeout=25)
        except requests.RequestException as error:
            print(f"\n### {label}: 异常 {error}")
            continue

        text = decode_bytes(response.content)
        payload = parse_feeds_payload(text)
        items = ((payload.get("data") or {}).get("data") or []) if isinstance(payload, dict) else []
        mine = sum(
            1
            for item in items
            if isinstance(item, dict) and credentials.uin in re.findall(r"fct_(\d+)_", item.get("html") or "")
        )
        print(f"\n### {label}  http={response.status_code} 条目={len(items)} 属于我={mine} 响应={len(text)}")
        for index, item in enumerate(items[:2]):
            if isinstance(item, dict):
                markup = item.get("html") or ""
                uins = sorted(set(re.findall(r"fct_(\d+)_", markup)))
                preview = " ".join(BeautifulSoup(markup, "html.parser").get_text(" ", strip=True).split())[:70]
                print(f"    #{index} uins={uins[:3]} | {preview}")
        time.sleep(2)

    return 0


DISPATCH = {
    "--feeds3": "probe_feeds3",
    "--selfscan": "self_scan",
    "--deep": "deep",
    "--hostuin": "probe_hostuin",
    "--recover": "recover",
    "--pageprobe": "page_probe",
    "--analyze": "analyze",
    "--why": "why_json5",
    "--page2": "page2",
    "--paging": "paging_variants",
    "--pageloop": "page_loop",
    "--empty": "empty_response",
}


def empty_response() -> int:
    """看第 3 页那个 127 字符的空响应到底是什么，并试几种游标写法。"""
    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    base = {
        "uin": credentials.uin,
        "hostuin": credentials.uin,
        "g_tk": credentials.gtk,
        "scope": 1,
        "view": 1,
        "filter": "all",
        "applist": "all",
        "fupdate": 1,
        "refresh": 0,
        "count": 30,
        "begintime": 1788097973,  # 第 2 页拿到的 basetime
    }

    response = session.get(FEEDS3_URL, params=base, timeout=30)
    text = decode_bytes(response.content)
    print(f"=== 原样请求（begintime=1788097973）{len(text)} 字符 ===")
    print(text[:300])

    variants = [
        ("begintime 字符串", {"begintime": "1788097973"}),
        ("begintime - 1", {"begintime": 1788097972}),
        ("begintime + endtime", {"begintime": 1788097973, "endtime": 1788927811}),
        ("count=50", {"count": 50}),
        ("去掉 fupdate/refresh", {"fupdate": 0, "refresh": 1}),
    ]
    for label, extra in variants:
        params = {**base, **extra}
        r = session.get(FEEDS3_URL, params=params, timeout=30)
        t = decode_bytes(r.content)
        items = len(re.findall(r"abstime:", t))
        print(f"  {label:<26} 长度={len(t):<7} 条目≈{items}")
        time.sleep(2)

    return 0


def page_loop(pages: int = 6) -> int:
    """用 begintime=basetime 连续翻页，确认时间能一路往回走。"""
    from datetime import datetime, timezone

    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    base = {
        "uin": credentials.uin,
        "hostuin": credentials.uin,
        "g_tk": credentials.gtk,
        "scope": 1,
        "view": 1,
        "filter": "all",
        "applist": "all",
        "fupdate": 1,
        "refresh": 0,
        "count": 30,
    }

    fmt = lambda t: datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    begintime = None
    seen: set[str] = set()

    for page in range(1, pages + 1):
        params = dict(base)
        if begintime:
            params["begintime"] = begintime
        try:
            response = session.get(FEEDS3_URL, params=params, timeout=30)
        except requests.RequestException as error:
            print(f"第 {page} 页异常: {error}")
            break

        text = decode_bytes(response.content)
        payload = parse_feeds_payload(text)
        outer = payload.get("data") or {}
        items = outer.get("data") or []
        main = outer.get("main") or {}

        if not items:
            print(f"第 {page} 页: 没有数据了（{len(text)} 字符），停")
            break

        stamps = sorted(int(i.get("abstime") or 0) for i in items if isinstance(i, dict) and i.get("abstime"))
        externparam = main.get("externparam") or ""
        new_base = ""
        for chunk in externparam.split("&"):
            if chunk.startswith("basetime="):
                new_base = chunk.split("=", 1)[1]

        fresh = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("abstime")) + (item.get("html") or "")[:60]
            if key not in seen:
                seen.add(key)
                fresh += 1

        print(
            f"第 {page} 页: 条目={len(items):<3} 新增={fresh:<3} "
            f"时间={fmt(stamps[0])} ~ {fmt(stamps[-1])}  basetime={new_base}"
        )

        if not new_base or new_base == begintime:
            print("    basetime 没往前走，停")
            break
        begintime = new_base
        time.sleep(2)

    return 0


def paging_variants() -> int:
    """把 externparam 拆成各种可能的参数形态，看哪种能翻动。"""
    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    base = {
        "uin": credentials.uin,
        "hostuin": credentials.uin,
        "g_tk": credentials.gtk,
        "scope": 1,
        "view": 1,
        "filter": "all",
        "applist": "all",
        "fupdate": 1,
        "refresh": 0,
        "count": 30,
    }

    baseline = session.get(FEEDS3_URL, params=base, timeout=30)
    base_text = decode_bytes(baseline.content)
    payload = parse_feeds_payload(base_text)
    externparam = ((payload.get("data") or {}).get("main") or {}).get("externparam") or ""
    print(f"基线响应 {len(base_text)} 字符，externparam={externparam[:120]}")

    # externparam 里其实是 offset/total/basetime/feedsource 这些字段
    fields: dict[str, str] = {}
    for chunk in externparam.split("&"):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            fields[key] = value
    print(f"拆出的字段: {list(fields)}")

    basetime = fields.get("basetime", "")

    variants = [
        ("拆平所有字段 + pagenum=2", {**fields, "pagenum": 2}),
        ("只给 basetime", {"basetime": basetime}),
        ("basetime + pagenum=2", {"basetime": basetime, "pagenum": 2}),
        ("endtime=basetime", {"endtime": basetime}),
        ("begintime=basetime", {"begintime": basetime}),
        ("refresh=1", {"refresh": 1}),
        ("offset/total + pagenum", {"offset": 30, "total": 31, "pagenum": 2}),
    ]

    for label, extra in variants:
        try:
            response = session.get(FEEDS3_URL, params={**base, **extra}, timeout=30)
        except requests.RequestException as error:
            print(f"  {label}: 异常 {error}")
            continue
        text = decode_bytes(response.content)
        items = len(re.findall(r"abstime:", text))
        same = "（与基线相同）" if text == base_text else ""
        print(f"  {label:<28} 长度={len(text):<8} 条目≈{items:<3} {same}")
        time.sleep(2)

    return 0


def page2() -> int:
    """用 main.externparam 翻下一页，确认能沿时间轴往回走。"""
    from datetime import datetime, timezone

    from qz_archive.parse import parse_feeds_payload

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    base = {
        "uin": credentials.uin,
        "hostuin": credentials.uin,
        "g_tk": credentials.gtk,
        "scope": 1,
        "view": 1,
        "filter": "all",
        "applist": "all",
        "fupdate": 1,
        "refresh": 0,
        "count": 30,
    }

    fmt = lambda t: datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    externparam = None

    for page in range(1, 6):
        # 注意：externparam 必须原样拼接，内部的 & 不能转义，否则服务端会忽略它
        if externparam:
            query = urlencode(base) + f"&externparam={externparam}&pagenum={page}"
            response = session.get(f"{FEEDS3_URL}?{query}", timeout=30)
        else:
            response = session.get(FEEDS3_URL, params=base, timeout=30)
        text = decode_bytes(response.content)
        payload = parse_feeds_payload(text)
        outer = payload.get("data") or {}
        items = outer.get("data") or []
        main = outer.get("main") or {}

        stamps = sorted(int(i.get("abstime") or 0) for i in items if isinstance(i, dict) and i.get("abstime"))
        span = f"{fmt(stamps[0])} ~ {fmt(stamps[-1])}" if stamps else "-"
        print(f"第 {page} 页: 条目={len(items):<3} 时间={span}  响应={len(text)}")

        first = next((i for i in items if isinstance(i, dict)), None)
        if first:
            preview = " ".join(
                BeautifulSoup(first.get("html") or "", "html.parser").get_text(" ", strip=True).split()
            )[:90]
            print(f"    {preview}")

        externparam = main.get("externparam")
        if not externparam:
            print("    没有 externparam，翻不动了")
            break
        time.sleep(2)

    return 0


def why_json5() -> int:
    """打印 json5 解析失败的位置附近的内容，找出让它解析不了的地方。"""
    import json5

    from qz_archive.parse import LAST_JSON5_ERROR, strip_callback

    raw = Path("/tmp/self_feed_raw.txt").read_text(encoding="utf-8", errors="replace")
    inner = strip_callback(raw)
    message = ""
    try:
        json5.loads(inner)
        print("这次居然解析成功了")
        return 0
    except Exception as error:  # noqa: BLE001
        message = str(error)
        print(f"错误: {message}")

    match = re.search(r"column (\d+)", message or LAST_JSON5_ERROR[0])
    position = int(match.group(1)) if match else len(inner) // 2
    print(f"\n=== 位置 {position} 前后各 160 字符 ===")
    start = max(0, position - 160)
    print(repr(inner[start : position + 160]))

    return 0


def analyze() -> int:
    """拆解 /tmp/self_feed_raw.txt：时间跨度、main 字段、以及单条记录的 HTML。"""
    from qz_archive.parse import parse_feeds_payload

    raw = Path("/tmp/self_feed_raw.txt").read_text(encoding="utf-8", errors="replace")
    payload = parse_feeds_payload(raw)
    outer = payload.get("data") or {}
    items = outer.get("data") or []

    print(f"条目数: {len(items)}")
    print(f"main: {outer.get('main')}")

    stamps = sorted(int(item.get("abstime") or 0) for item in items if isinstance(item, dict))
    if stamps:
        from datetime import datetime, timezone

        fmt = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"时间跨度: {fmt(stamps[0])} ~ {fmt(stamps[-1])}")

    for item in items:
        if not isinstance(item, dict):
            continue
        markup = item.get("html") or ""
        soup = BeautifulSoup(markup, "html.parser")
        classes = sorted({c for node in soup.find_all(True) for c in (node.get("class") or [])})
        if classes:
            print(f"\n=== 样本条目 ===")
            print(f"abstime={item.get('abstime')} 字段={[k for k in item if k != 'html']}")
            print(f"标签 class: {classes[:25]}")
            imgs = [img.get("src") for img in soup.find_all("img") if img.get("src")]
            print(f"图片({len(imgs)}): {[u[:70] for u in imgs[:4]]}")
            print("正文:", " ".join(soup.get_text(" ", strip=True).split())[:200])
            Path("/tmp/self_feed_item.html").write_text(markup, encoding="utf-8")
            print("该条 HTML 已写到 /tmp/self_feed_item.html")
            break

    return 0


def page_probe() -> int:
    """查「与我相关」的翻页方式：看 main 游标，并试各种分页参数。"""
    from datetime import datetime, timezone

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    base = {
        "uin": credentials.uin,
        "hostuin": credentials.uin,
        "g_tk": credentials.gtk,
        "scope": 1,
        "view": 1,
        "filter": "all",
        "applist": "all",
        "fupdate": 1,
        "refresh": 0,
        "count": 30,
    }

    now = int(datetime.now(tz=timezone.utc).timestamp())
    variants = [
        ("基线（无时间参数）", {}),
        ("begintime/endtime=0", {"begintime": 0, "endtime": 0}),
        ("begin_time/end_time=0", {"begin_time": 0, "end_time": 0}),
        ("begintime=2年前", {"begintime": now - 2 * 365 * 86400, "endtime": 0}),
        ("pos=31", {"pos": 31}),
        ("page=2", {"page": 2}),
        ("offset=31", {"offset": 31}),
    ]

    for label, extra in variants:
        try:
            response = session.get(FEEDS3_URL, params={**base, **extra}, timeout=30)
        except requests.RequestException as error:
            print(f"\n### {label}: 异常 {error}")
            continue

        text = decode_bytes(response.content)
        uins = set(re.findall(r"fct_(\d+)_", text))
        items = len(re.findall(r"abstime:", text))
        main_hit = re.search(r"main:\s*\{", text)
        main_snippet = ""
        if main_hit:
            main_snippet = " ".join(text[main_hit.start() : main_hit.start() + 260].split())

        print(f"\n### {label}  http={response.status_code} 长度={len(text)} 条目≈{items} uin数={len(uins)}")
        print(f"    {main_snippet}")

        if label.startswith("基线"):
            Path("/tmp/self_feed_raw.txt").write_text(text, encoding="utf-8")
        time.sleep(2)

    print("\n基线响应已存 /tmp/self_feed_raw.txt")
    return 0


def fetch_self_feed(session, credentials, begintime: int, endtime: int, count: int = 30):
    """带 hostuin 拉「与我相关」的一窗数据，返回 (items, 原始文本)。"""
    from qz_archive.parse import parse_feeds_payload

    params = {
        "uin": credentials.uin,
        "hostuin": credentials.uin,
        "g_tk": credentials.gtk,
        "scope": 1,
        "view": 1,
        "filter": "all",
        "applist": "all",
        "fupdate": 1,
        "refresh": 0,
        "begintime": begintime,
        "endtime": endtime,
        "count": count,
    }
    response = session.get(FEEDS3_URL, params=params, timeout=30)
    text = decode_bytes(response.content)
    payload = parse_feeds_payload(text)
    items = ((payload.get("data") or {}).get("data") or []) if isinstance(payload, dict) else []
    return items, text


def recover() -> int:
    """按时间窗往回翻「与我相关」，并把一条的 HTML 结构打出来。"""
    from datetime import datetime, timezone

    credentials = read_cookie_file(Path.home() / "personal-site" / "secrets" / "cookie.txt")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DESKTOP_UA,
            "Referer": f"{QZONE_BASE}/{credentials.uin}/main",
            "Cookie": credentials.raw_cookie,
        }
    )

    now = int(datetime.now(tz=timezone.utc).timestamp())
    half_year = 182 * 86400

    print("=== 按半年往回翻「与我相关」 ===")
    all_previews: list[str] = []
    for step in range(8):
        end = now - step * half_year
        begin = end - half_year
        try:
            items, text = fetch_self_feed(session, credentials, begin, end)
        except requests.RequestException as error:
            print(f"  step={step}: 异常 {error}")
            continue

        label = datetime.fromtimestamp(end, tz=timezone.utc).strftime("%Y-%m")
        print(f"  {label} 之前半年: 条目={len(items):<3} 响应={len(text)}")

        for item in items:
            if not isinstance(item, dict):
                continue
            markup = item.get("html") or ""
            preview = " ".join(BeautifulSoup(markup, "html.parser").get_text(" ", strip=True).split())
            if preview:
                all_previews.append(f"[{label}] {preview[:150]}")
            if step == 0 and item is items[0]:
                Path("/tmp/self_feed_item.html").write_text(markup, encoding="utf-8")
        time.sleep(2)

    print(f"\n共取到 {len(all_previews)} 条互动记录，示例：")
    for entry in all_previews[:12]:
        print(f"  {entry}")

    print("\n第一条的 HTML 已写到 /tmp/self_feed_item.html")
    return 0


def run() -> int:
    """入口放在文件最后，避免函数还没定义就被调用。"""
    for flag, name in DISPATCH.items():
        if flag in sys.argv:
            return globals()[name]()
    return try_endpoints() if "--try" in sys.argv else main()


if __name__ == "__main__":
    raise SystemExit(run())
