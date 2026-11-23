from __future__ import annotations

import datetime
from pathlib import Path

import apprise
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .moddb_client import Comment, MemberComments
from .settings import MessageFormat

BUILTIN_TEMPLATE_DIR = Path(__file__).parent / "templates"
BODY_TEMPLATES: dict[MessageFormat, str] = {"markdown": "body.md.j2", "html": "body.html.j2", "text": "body.txt.j2"}


def create_environment(template_dir: Path | None) -> Environment:
    """User templates take precedence; missing files fall back to the built-in ones."""
    search_path = [template_dir, BUILTIN_TEMPLATE_DIR] if template_dir else [BUILTIN_TEMPLATE_DIR]
    env = Environment(
        loader=FileSystemLoader(search_path),
        undefined=StrictUndefined,
        # Comment text is user content: escape it in HTML templates, but never in the plain-text title
        autoescape=select_autoescape(enabled_extensions=("html.j2",), default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )
    # Two trailing spaces are a Markdown hard line break, so multi-line comments keep their lines in HTML
    env.filters["quote"] = lambda text: "  \n".join(f"> {line}" for line in text.splitlines() or [""])
    return env


def render(env: Environment, result: MemberComments, message_format: MessageFormat) -> tuple[str, str]:
    context = {"member": result.member, "comments": result.comments}
    title = env.get_template("title.j2").render(context)
    body = env.get_template(BODY_TEMPLATES[message_format]).render(context)
    return " ".join(title.split()), body.strip()


SAMPLE_COMMENTS = [
    Comment(
        id=1001,
        author="Alice",
        content="Love it!\nAny plans for a v2?",
        addon="Better Textures",
        addon_url="https://www.moddb.com/addons/better-textures",
        url="https://www.moddb.com/addons/better-textures/page/1#1001",
        date=datetime.datetime(2026, 1, 2, 14, 5, tzinfo=datetime.UTC),
        has_time=True,
    ),
    Comment(
        id=1002,
        author="Bob",
        content="Crashes on start with <Patch 1.2> :(",
        addon="HUD Mod",
        addon_url="https://www.moddb.com/addons/hud-mod",
        url="https://www.moddb.com/addons/hud-mod/page/3#1002",
        date=datetime.datetime(2026, 1, 2),
        has_time=False,
    ),
]


def preview(env: Environment, message_format: MessageFormat) -> str:
    """Render the templates with sample data for a single comment and for several comments."""
    sections = []
    for label, comments in [("1 comment", SAMPLE_COMMENTS[:1]), ("2 comments", SAMPLE_COMMENTS)]:
        title, body = render(env, MemberComments(member="YourName", comments=comments), message_format)
        sections.append(f"---- {label} ({message_format}) ----\nTitle: {title}\n\n{body}")
    return "\n\n".join(sections)


def send(notify_url: str, title: str, body: str, message_format: MessageFormat) -> bool:
    apobj = apprise.Apprise()
    apobj.add(notify_url)
    return bool(apobj.notify(title=title, body=body, body_format=apprise.NotifyFormat(message_format)))
