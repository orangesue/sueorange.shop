"""合并层单测：决定「哪条是找回的」的规则都在这里。"""

from qz_archive.merge import merge_posts, normalize_text


def make_msglist_post(**overrides):
    post = {
        "id": "t1",
        "tid": "t1",
        "createdAt": "2020-05-01T02:00:00Z",
        "text": "现存的一条说说",
        "images": ["http://example.com/a.jpg"],
        "comments": [{"author": "甲", "text": "在", "createdAt": ""}],
        "likes": 3,
        "deleted": False,
        "source": "msglist",
        "repost": None,
    }
    post.update(overrides)
    return post


def make_feed_post(**overrides):
    post = {
        "id": "",
        "tid": "",
        "createdAt": "2020-05-01T02:00:00Z",
        "text": "现存的一条说说",
        "images": ["http://example.com/b.jpg"],
        "comments": [],
        "likes": 5,
        "deleted": False,
        "source": "feeds",
        "repost": None,
    }
    post.update(overrides)
    return post


def test_empty_input():
    assert merge_posts([], []) == []


def test_feed_only_post_is_marked_as_recovered():
    posts = merge_posts([], [make_feed_post(text="早就删掉的一条")])

    assert len(posts) == 1
    assert posts[0]["deleted"] is True
    assert posts[0]["source"] == "feeds"
    assert posts[0]["id"]  # 没有 tid 时也要有稳定 id


def test_same_tid_merges_into_both():
    posts = merge_posts(
        [make_msglist_post(tid="t1")],
        [make_feed_post(tid="t1")],
    )

    assert len(posts) == 1
    post = posts[0]
    assert post["source"] == "both"
    assert post["deleted"] is False
    assert post["images"] == ["http://example.com/a.jpg", "http://example.com/b.jpg"]
    assert post["likes"] == 5


def test_same_time_and_text_merges_without_tid():
    posts = merge_posts(
        [make_msglist_post(tid="t9", text="内容一样")],
        [make_feed_post(text="内容一样")],
    )

    assert len(posts) == 1
    assert posts[0]["source"] == "both"
    assert posts[0]["tid"] == "t9"


def test_duplicate_feed_entries_are_deduped_and_stay_recovered():
    feed = make_feed_post(text="只剩互动记录的一条")
    posts = merge_posts([], [feed, dict(feed)])

    assert len(posts) == 1
    assert posts[0]["deleted"] is True
    assert posts[0]["source"] == "feeds"


def test_comments_are_deduped_when_merging():
    comment = {"author": "甲", "text": "在", "createdAt": ""}
    posts = merge_posts(
        [make_msglist_post(comments=[comment])],
        [make_feed_post(tid="t1", comments=[dict(comment)])],
    )

    assert len(posts[0]["comments"]) == 1


def test_feed_entry_without_text_or_images_is_dropped():
    assert merge_posts([], [make_feed_post(text="", images=[])]) == []


def test_normalize_text_ignores_spaces_and_case():
    assert normalize_text(" Hello  World ") == "helloworld"

