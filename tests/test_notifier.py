from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from moddb_comment_notifier import __main__, app, moddb_client, notify
from moddb_comment_notifier.moddb_client import Comment, MemberComments
from moddb_comment_notifier.settings import Settings
from moddb_comment_notifier.state import State

NOTIFY_URL = "json://localhost/"


def make_comment(author: str = "Alice", addon: str = "Cool Addon", content: str = "Nice!", id: int = 42) -> Comment:
    return Comment(
        id=id,
        author=author,
        content=content,
        addon=addon,
        addon_url="https://www.moddb.com/addons/cool-addon",
        url=f"https://www.moddb.com/addons/cool-addon/page/1#{id}",
        date=datetime.datetime(2026, 1, 2, 3, 4, tzinfo=datetime.UTC),
        has_time=True,
    )


@pytest.fixture
def settings(tmp_path, monkeypatch) -> Settings:
    monkeypatch.chdir(tmp_path)  # don't pick up a developer's .env
    return Settings(member="tosox", notify_url=NOTIFY_URL, state_dir=tmp_path)


# Settings


def test_settings_from_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MCN_MEMBER", " tosox ")
    monkeypatch.setenv("MCN_NOTIFY_URL", NOTIFY_URL)
    monkeypatch.setenv("MCN_INTERVAL", "5")

    settings = Settings()

    assert settings.member == "tosox"
    assert settings.interval == 5
    assert not settings.moddb_login_enabled


def test_settings_reject_invalid_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError) as exc:
        Settings(member="", notify_url="not-a-url", interval=0)
    assert {err["loc"][0] for err in exc.value.errors()} == {"member", "notify_url", "interval"}


def test_settings_reject_multiple_urls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError):
        Settings(member="tosox", notify_url=f"{NOTIFY_URL} json://otherhost/")


def test_secrets_are_hidden(settings):
    assert NOTIFY_URL not in repr(settings)


# State


def test_state_roundtrip(tmp_path):
    State(last_comment_id=123, session_cookie="abc").save(tmp_path)
    assert State.load(tmp_path) == State(last_comment_id=123, session_cookie="abc")


def test_state_missing_or_corrupt(tmp_path):
    assert State.load(tmp_path) == State()
    (tmp_path / "state.json").write_text("{not json", encoding="utf-8")
    assert State.load(tmp_path) == State()


# Templates


def test_render_single_comment():
    env = notify.create_environment(None)
    title, body = notify.render(env, MemberComments("Tosox", [make_comment(content="line 1\nline 2")]), "markdown")

    assert title == "Alice commented on Cool Addon"
    assert "Hi Tosox," in body
    assert "[Cool Addon](https://www.moddb.com/addons/cool-addon)" in body
    assert "[View comment ↗](https://www.moddb.com/addons/cool-addon/page/1#42)" in body
    assert "> line 1  \n> line 2" in body
    assert "at 02.01.2026 03:04:" in body


def test_render_multiple_comments():
    env = notify.create_environment(None)
    comments = [make_comment(), make_comment(author="Bob", id=43)]
    title, _ = notify.render(env, MemberComments("Tosox", comments), "markdown")
    assert title == "2 new comments on your add-ons"


def test_user_template_overrides_builtin(tmp_path):
    (tmp_path / "title.j2").write_text("Custom {{ comments | length }}", encoding="utf-8")
    env = notify.create_environment(tmp_path)
    title, body = notify.render(env, MemberComments("Tosox", [make_comment()]), "markdown")

    assert title == "Custom 1"
    assert "Hi Tosox," in body  # body falls back to the built-in template


# Check cycle


@pytest.fixture
def fake_moddb(monkeypatch):
    sent: list[tuple[str, str]] = []
    result = {"comments": [make_comment()], "send_ok": True, "fail": False}

    def fetch(member, after_id):
        if result["fail"]:
            raise ConnectionError("moddb down")
        return MemberComments("Tosox", result["comments"])

    def send(url, title, body, message_format):
        sent.append((title, body))
        return result["send_ok"]

    monkeypatch.setattr(moddb_client, "fetch_new_comments", fetch)
    monkeypatch.setattr(notify, "send", send)
    return result, sent


def test_first_run_saves_newest_comment_without_notifying(settings, fake_moddb):
    _, sent = fake_moddb
    state = State()
    app.check(settings, notify.create_environment(None), state)

    assert state.last_comment_id == 42
    assert sent == []


def test_successful_check_advances_state(settings, fake_moddb):
    _, sent = fake_moddb
    state = State(last_comment_id=10)
    app.check(settings, notify.create_environment(None), state)

    assert state.last_comment_id == 42
    assert len(sent) == 1


def test_check_without_new_comments_keeps_state(settings, fake_moddb):
    result, sent = fake_moddb
    result["comments"] = []
    state = State(last_comment_id=10)
    app.check(settings, notify.create_environment(None), state)

    assert state.last_comment_id == 10
    assert sent == []


@pytest.mark.parametrize("failure", ["send_failed", "fetch_failed"])
def test_failures_keep_state_for_retry(settings, fake_moddb, failure):
    result, _ = fake_moddb
    result["send_ok"] = failure != "send_failed"
    result["fail"] = failure == "fetch_failed"
    state = State(last_comment_id=10)
    app.check(settings, notify.create_environment(None), state)

    assert state.last_comment_id == 10


# Fetching


def fake_comment(id: int, author: str = "Alice", date: datetime.datetime | None = None) -> SimpleNamespace:
    date = date or datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    return SimpleNamespace(id=id, author=SimpleNamespace(name=author), content=f"\ncomment {id}\n", date=date)


class FakePage(list):
    def __init__(self, pages: list[list[SimpleNamespace]], number: int):
        super().__init__(pages[number - 1])
        self.pages, self.current_page, self.total_pages = pages, number, len(pages)

    def to_page(self, number: int) -> FakePage:
        return FakePage(self.pages, number)


def test_fetch_new_comments_by_id_with_comment_links(monkeypatch):
    # Oldest first on each page, like ModDB. 103 only has a date, which made it look older than the last check
    pages = [
        [fake_comment(90), fake_comment(95)],
        [fake_comment(100), fake_comment(101, author="Tosox"), fake_comment(103, date=datetime.datetime(2026, 1, 1))],
        [fake_comment(102, date=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC))],
    ]
    url = "https://www.moddb.com/mods/x/addons/cool"
    addon = SimpleNamespace(name="Cool", url=url, parse=lambda: SimpleNamespace(comments=FakePage(pages, 1)))
    member = SimpleNamespace(name="Tosox", get_addons=lambda: [addon])
    monkeypatch.setattr(moddb_client.moddb, "parse_page", lambda _: member)

    result = moddb_client.fetch_new_comments("tosox", after_id=95)

    assert [(c.id, c.url) for c in result.comments] == [
        (100, f"{url}/page/2#100"),
        (102, f"{url}/page/3#102"),
        (103, f"{url}/page/2#103"),
    ]
    assert [c.has_time for c in result.comments] == [True, True, False]
    assert result.comments[0].addon_url == url
    assert result.comments[0].content == "comment 100"


def test_log_level_is_case_insensitive_and_validated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Settings(member="tosox", notify_url=NOTIFY_URL, log_level="debug").log_level == "DEBUG"
    with pytest.raises(ValidationError):
        Settings(member="tosox", notify_url=NOTIFY_URL, log_level="verbose")


# Preview


def test_preview_renders_single_and_multiple_comments():
    output = notify.preview(notify.create_environment(None), "markdown")
    assert "Title: Alice commented on Better Textures" in output
    assert "Title: 2 new comments on your add-ons" in output


def test_preview_cli_works_without_full_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCN_MEMBER", raising=False)
    monkeypatch.delenv("MCN_NOTIFY_URL", raising=False)
    (tmp_path / "title.j2").write_text("Custom title", encoding="utf-8")
    monkeypatch.setenv("MCN_TEMPLATE_DIR", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["moddb-comment-notifier", "--preview"])

    __main__.main()

    assert "Title: Custom title" in capsys.readouterr().out


def test_preview_cli_reports_template_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "body.md.j2").write_text("Hi {{ member }\n", encoding="utf-8")
    monkeypatch.setenv("MCN_TEMPLATE_DIR", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["moddb-comment-notifier", "--preview"])

    with pytest.raises(SystemExit, match=r"Template error in .*body\.md\.j2, line 1"):
        __main__.main()


# Message formats


def test_html_body_escapes_comment_but_not_title():
    env = notify.create_environment(None)
    comment = make_comment(author="A&B", content="<script>alert(1)</script>")
    title, body = notify.render(env, MemberComments("Tosox", [comment]), "html")

    assert title == "A&B commented on Cool Addon"
    assert "<script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert '<a href="https://www.moddb.com/addons/cool-addon"' in body
    assert '<a href="https://www.moddb.com/addons/cool-addon/page/1#42"' in body


def test_text_body_is_plain():
    env = notify.create_environment(None)
    _, body = notify.render(env, MemberComments("Tosox", [make_comment(content="line 1\nline 2")]), "text")

    assert "    line 1\n    line 2" in body
    assert "https://www.moddb.com/addons/cool-addon" in body
    assert "**" not in body


def test_message_format_is_case_insensitive_and_validated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Settings(member="tosox", notify_url=NOTIFY_URL, message_format="HTML").message_format == "html"
    with pytest.raises(ValidationError):
        Settings(member="tosox", notify_url=NOTIFY_URL, message_format="rtf")


# HTTP stack


def test_moddb_http_stack_works():
    """Catches incompatible versions of curl_adapter, curl_cffi and urllib3, using a local server only."""
    import http.server
    import threading

    import moddb

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        response = moddb.SESSION.get(f"http://127.0.0.1:{server.server_port}/")
        assert response.status_code == 200
        assert response.text == "ok"
    finally:
        server.shutdown()


@pytest.mark.parametrize("message_format", ["markdown", "html", "text"])
def test_date_only_comment_shows_no_time(message_format):
    comment = make_comment()
    comment = Comment(**{**vars(comment), "date": datetime.datetime(2026, 11, 11), "has_time": False})
    _, body = notify.render(notify.create_environment(None), MemberComments("Tosox", [comment]), message_format)

    assert "at 11.11.2026" in body
    assert "00:00" not in body
