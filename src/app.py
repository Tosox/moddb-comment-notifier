from __future__ import annotations

import datetime
import time

import schedule

from .config import (
    delete_session_cookie,
    get_last_checked,
    load_settings,
    save_last_checked,
    write_session_cookie,
)
from .mailer import send_emails
from .moddb_client import get_current_session_cookie, login, process_member_comments
from .models import Settings


def run_once(settings: Settings) -> None:
    now = datetime.datetime.now(datetime.UTC)
    print(f"Running at {now:%d. %B %Y %H:%M:%S}")
    last_checked = get_last_checked(settings)
    new_timestamp = int(now.timestamp())

    auth_result = login(settings)
    try:
        all_messages = []
        for member in settings.members:
            all_messages.extend(process_member_comments(settings, member, last_checked))

        send_emails(settings, all_messages)
        save_last_checked(settings, new_timestamp)
    finally:
        session_cookie = get_current_session_cookie()
        if session_cookie:
            write_session_cookie(settings, session_cookie)
        elif auth_result.cookie_invalid and delete_session_cookie(settings):
            print("Deleted stale session cookie file after failed cookie login")

    print("Finished loop")


def run_forever() -> None:
    settings = load_settings()
    run_once(settings)
    schedule.every(settings.schedule_interval).minutes.do(run_once, settings=settings)
    while True:
        schedule.run_pending()
        time.sleep(1)
