from __future__ import annotations

import logging
import threading
import time

from jinja2 import Environment

from . import moddb_client, notify
from .settings import Settings
from .state import State

log = logging.getLogger(__name__)


def check(settings: Settings, env: Environment, state: State) -> None:
    started = int(time.time())
    if state.last_checked is None:
        log.info("First run: saved the current time, comments posted after it will be reported from the next check on")
        state.last_checked = started
        return

    try:
        result = moddb_client.fetch_new_comments(settings.member, state.last_checked)
    except Exception as exc:
        log.error("Failed to fetch comments, retrying next run: %s", exc)
        return

    log.info("%d new comment(s)", len(result.comments))
    if result.comments:
        title, body = notify.render(env, result, settings.message_format)
        if not notify.send(settings.notify_url.get_secret_value(), title, body, settings.message_format):
            log.error("Failed to send notification, retrying next run")
            return

    state.last_checked = started


def run_once(settings: Settings, env: Environment) -> None:
    state = State.load(settings.state_dir)
    state.session_cookie = moddb_client.login(
        state.session_cookie,
        settings.moddb_username,
        settings.moddb_password.get_secret_value(),
    )
    check(settings, env, state)
    state.save(settings.state_dir)


def run_forever(settings: Settings, env: Environment, stop: threading.Event) -> None:
    while not stop.is_set():
        run_once(settings, env)
        log.info("Next check in %d minute(s)", settings.interval)
        stop.wait(settings.interval * 60)
