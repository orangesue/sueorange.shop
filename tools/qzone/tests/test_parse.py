"""解析层单测：不联网，只用 fixture。"""

from qz_archive.parse import (
    clean_html_text,
    decode_bytes,
    parse_feeds_html,
    parse_msglist_jsonp,
    parse_msglist_to_posts,
    strip_jsonp,
    text_time_to_iso,
    unix_to_iso,
)
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_decode_bytes_handles_gbk():
    payload = "今天天气不错".encode("gbk")
    assert decode_bytes(payload) == "今天天气不错"


def test_decode_bytes_handles_utf8():
    payload = "今天天气不错".encode("utf-8")
    assert decode_bytes(payload) == "今天天气不错"


def test_strip_jsonp():
    assert strip_jsonp('_preloadCallback({"a":1});') == '{"a":1}'
    assert strip_jsonp('{"a":1}') == '{"a":1}'


def test_parse_msglist_jsonp_returns_empty_on_garbage():
    assert parse_msglist_jsonp("<html>登录</html>")["msglist"] == []
    assert parse_msglist_jsonp("_preloadCallback([1,2,3]);")["msglist"] == []


def test_parse_msglist_to_posts():
    posts = parse_msglist_to_posts(read("msglist_sample.jsonp"))

    assert len(posts) == 2
    first = posts[0]
    assert first["tid"] == "abc1234567890"
    # 表情占位符会被清掉，HTML 会被还原成纯文本
    assert "[em]" not in first["text"]
    assert "今天天气不错" in first["text"]
    # 三档图里取最清晰的一档
    assert first["images"] == ["http://photo.store.qq.com/psb?/big.jpg"]
    assert first["comments"][0]["author"] == "小明"
    assert first["comments"][0]["createdAt"] == unix_to_iso(1580000100)
    assert first["repost"] == "转发的原文"
    assert first["deleted"] is False
    assert first["source"] == "msglist"


def test_parse_msglist_skips_records_without_identity():
    posts = parse_msglist_to_posts('_preloadCallback({"msglist":[{"content":""}]});')
    assert posts == []


def test_clean_html_text_strips_tags_and_entities():
    result = clean_html_text("<b>你好</b>&nbsp;世界")
    assert "<b>" not in result
    assert "你好" in result and "世界" in result


def test_unix_to_iso_invalid():
    assert unix_to_iso("abc") == ""
    assert unix_to_iso(0) == ""
    assert unix_to_iso(1580000000) == "2020-01-26T00:53:20Z"


def test_text_time_to_iso_uses_beijing_time():
    # 北京时间 15:45 -> UTC 07:45
    assert text_time_to_iso("2020年2月14日 15:45") == "2020-02-14T07:45:00Z"
    assert text_time_to_iso("没有时间") == ""


def test_parse_feeds_html():
    posts = parse_feeds_html(read("feed_sample.html"))

    assert len(posts) == 3

    first = posts[0]
    assert first["tid"] == "xyz789abc"
    assert first["createdAt"] == "2020-02-14T07:45:00Z"
    assert first["text"] == "这一条早就被我删掉了"
    # 头像（qlogo）被过滤，只留下真正的配图
    assert first["images"] == ["https://photo.store.qq.com/psb?/deleted-1.jpg"]

    second = posts[1]
    assert second["tid"] == ""
    assert second["images"] == []
    assert second["createdAt"] == "2020-01-01T00:30:00Z"


def test_parse_feeds_html_on_empty_or_broken_input():
    assert parse_feeds_html("") == []
    assert parse_feeds_html("<html><body><p>登录</p></body></html>") == []
