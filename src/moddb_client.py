from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage

import moddb
import moddb.errors

from .config import read_session_cookie
from .mailer import create_email
from .models import Member, Settings


@dataclass(frozen=True)
class AuthResult:
    cookie_invalid: bool = False


def get_current_session_cookie() -> str | None:
    value = moddb.get_freeman_cookie()
    if not value:
        return None
    return value.strip() or None


def login(settings: Settings) -> AuthResult:
    cookie_invalid = False
    session_cookie = read_session_cookie(settings)
    if session_cookie:
        try:
            moddb.login(freeman_cookie=session_cookie)
            return AuthResult(cookie_invalid=False)
        except (moddb.errors.AuthError, ValueError) as exc:
            cookie_invalid = True
            print(f"Stored session cookie login failed, falling back to username and password: {exc}")
        except Exception as exc:
            cookie_invalid = True
            print(f"Stored session cookie login failed unexpectedly, falling back to username and password: {exc}")

    username = settings.moddb_username.strip()
    password = settings.moddb_password.strip()
    if not username and not password:
        print("No ModDB credentials configured; continuing without authenticated session")
        return AuthResult(cookie_invalid=cookie_invalid)
    if not username or not password:
        print("Skipping ModDB login fallback: set both username and password")
        return AuthResult(cookie_invalid=cookie_invalid)

    try:
        moddb.login(username, password)
    except moddb.errors.AuthError as exc:
        print(f"Unable to read guest comments, disable 2FA for this ModDB account: {exc}")
    except ValueError as exc:
        print(f"Unable to read guest comment, invalid login credentials: {exc}")
    except Exception as exc:
        print(f"Unable to read guest comments, unexpected login error: {exc}")

    return AuthResult(cookie_invalid=cookie_invalid)


def process_member_comments(
    settings: Settings,
    member: Member,
    last_checked: int,
) -> list[EmailMessage]:
    print(f"Checking user {member.uid}")
    try:
        member_obj = moddb.parse_page(f"{moddb.BASE_URL}/members/{member.uid}")
    except Exception as exc:
        print(f"Failed to retrieve member page: {exc}")
        return []

    messages: list[EmailMessage] = []
    for addon_thumb in member_obj.get_addons():
        print(f" Checking add-on: {addon_thumb.name}")
        try:
            comments = addon_thumb.parse().comments
        except Exception as exc:
            print(f"Failed to retrieve comments: {exc}")
            continue

        stop_early = False
        for page in range(comments.total_pages, 0, -1):
            for comment in reversed(comments.to_page(page)):
                timestamp = int(comment.date.timestamp())
                if timestamp <= last_checked:
                    stop_early = True
                    break
                if comment.author.name == member_obj.name:
                    continue

                print(f"  Found new comment by {comment.author.name}")
                messages.append(
                    create_email(
                        settings=settings,
                        member_name=member_obj.name,
                        member_email=member.email,
                        author=comment.author.name,
                        content=comment.content,
                        url=addon_thumb.url,
                    )
                )
            if stop_early:
                break

    return messages
