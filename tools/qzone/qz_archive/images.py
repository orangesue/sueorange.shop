"""配图下载：只在本机落盘，路径写进 JSON 供站点直接引用。"""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any

import requests

SAFE_NAME = re.compile(r"[^0-9a-zA-Z_-]")
MAX_BYTES = 20 * 1024 * 1024


def guess_extension(url: str, content_type: str | None) -> str:
    if content_type:
        extension = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if extension in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            return ".jpg" if extension == ".jpe" else extension

    suffix = Path(url.split("?")[0]).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def download_image(
    session: requests.Session,
    url: str,
    target: Path,
    *,
    referer: str,
    timeout: int = 20,
) -> bool:
    """下载单张图片；已存在则跳过。任何失败都只返回 False，不中断整体抓取。"""
    if target.exists() and target.stat().st_size > 0:
        return True

    try:
        response = session.get(
            url,
            headers={"Referer": referer},
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException:
        return False

    extension = guess_extension(url, response.headers.get("Content-Type"))
    target = target.with_suffix(extension)
    target.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                written += len(chunk)
                if written > MAX_BYTES:
                    raise ValueError("图片过大")
                handle.write(chunk)
    except (requests.RequestException, ValueError, OSError):
        target.unlink(missing_ok=True)
        return False
    finally:
        response.close()

    return written > 0


def localize_post_images(
    session: requests.Session,
    post: dict[str, Any],
    images_dir: Path,
    *,
    referer: str,
    relative_prefix: str = "data/images",
) -> None:
    """把 post['images'] 里的远程地址换成本地相对路径；失败的保留原链接。"""
    tid = post.get("tid") or post.get("id") or "unknown"
    folder = images_dir / SAFE_NAME.sub("_", str(tid))
    localized: list[str] = []

    for index, url in enumerate(post.get("images", []), start=1):
        if not url.startswith("http"):
            localized.append(url)
            continue

        target = folder / f"{index}"
        if download_image(session, url, target, referer=referer):
            actual = next(target.parent.glob(f"{index}.*"), None)
            if actual is not None:
                localized.append(f"{relative_prefix}/{folder.name}/{actual.name}")
                continue
        localized.append(url)

    post["images"] = localized

