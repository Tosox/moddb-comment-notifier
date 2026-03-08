from __future__ import annotations

import datetime
import time

import schedule

from .config import get_last_checked, load_settings, save_last_checked
from .mailer import send_emails
from .moddb_client import login, process_member_comments
from .models import Settings


def run_once(settings: Settings) -> None:
    now = datetime.datetime.now(datetime.UTC)
    print(f"Running at {now:%d. %B %Y %H:%M:%S}")
    last_checked = get_last_checked(settings)
    new_timestamp = int(now.timestamp())

    login(settings)

    all_messages = []
    for member in settings.members:
        all_messages.extend(process_member_comments(settings, member, last_checked))

    send_emails(settings, all_messages)
    save_last_checked(settings, new_timestamp)
    print("Finished loop")


def run_forever() -> None:
    settings = load_settings()
    run_once(settings)
    schedule.every(settings.schedule_interval).minutes.do(run_once, settings=settings)
    while True:
        schedule.run_pending()
        time.sleep(1)
