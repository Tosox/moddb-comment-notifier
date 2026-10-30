from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

import moddb
import moddb.errors

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Comment:
    author: str
    content: str
    addon: str
    url: str
    date: datetime.datetime


@dataclass(frozen=True)
class MemberComments:
    member: str
    comments: list[Comment]


def login(session_cookie: str | None, username: str, password: str) -> str | None:
    """Log into ModDB so guest comments become visible. Returns the session cookie to persist."""
    if session_cookie:
        try:
            moddb.login(freeman_cookie=session_cookie)
            return moddb.get_freeman_cookie()
        except Exception as exc:
            log.warning("Stored ModDB session is no longer valid: %s", exc)

    if not (username and password):
        return None

    try:
        moddb.login(username, password)
    except moddb.errors.AuthError as exc:
        log.error("ModDB login requires 2FA, disable it for this account: %s", exc)
    except Exception as exc:
        log.error("ModDB login failed: %s", exc)
    return moddb.get_freeman_cookie()


def fetch_new_comments(uid: str, since: int) -> MemberComments:
    """Return all comments on the member's add-ons posted after `since` (Unix timestamp).

    Raises on any network or parsing error so the caller does not advance its state.
    """
    member = moddb.parse_page(f"{moddb.BASE_URL}/members/{uid}")
    comments: list[Comment] = []

    for addon in member.get_addons():
        log.debug("Checking add-on %s", addon.name)
        first_page = addon.parse().comments
        for page in range(first_page.total_pages, 0, -1):
            page_comments = first_page if page == first_page.current_page else first_page.to_page(page)
            new = [c for c in reversed(page_comments) if c.date.timestamp() > since]
            comments.extend(
                Comment(
                    author=c.author.name,
                    content=(c.content or "").strip(),
                    addon=addon.name,
                    url=addon.url,
                    date=c.date,
                )
                for c in new
                if c.author.name != member.name
            )
            if len(new) < len(page_comments):
                break

    comments.sort(key=lambda c: c.date)
    return MemberComments(member=member.name, comments=comments)
