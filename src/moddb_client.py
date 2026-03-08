from __future__ import annotations

from email.message import EmailMessage

import moddb
import moddb.errors

from .mailer import create_email
from .models import Member, Settings


def login(settings: Settings) -> None:
    username = settings.moddb_username.strip()
    password = settings.moddb_password.strip()
    if not username and not password:
        return
    if not username or not password:
        print("Skipping ModDB login: set both username and password.")
        return

    try:
        moddb.login(username, password)
    except moddb.errors.AuthError as exc:
        print(f"Unable to read guest comments: disable 2FA for this ModDB account. {exc}")
    except ValueError as exc:
        print(f"Unable to read guest comments: invalid login credentials. {exc}")


def process_member_comments(
    settings: Settings,
    member: Member,
    last_checked: int,
) -> list[EmailMessage]:
    print(f"Checking user {member.uid}")
    try:
        member_obj = moddb.parse_page(f"f{moddb.BASE_URL}/members/{member.uid}")
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
