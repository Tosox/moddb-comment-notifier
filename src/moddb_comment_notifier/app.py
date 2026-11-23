from __future__ import annotations

import logging
import threading

from jinja2 import Environment

from . import moddb_client, notify
from .settings import Settings
from .state import State

log = logging.getLogger(__name__)


def check(settings: Settings, env: Environment, state: State) -> None:
    first_run = state.last_comment_id is None
    try:
        result = moddb_client.fetch_new_comments(settings.member, state.last_comment_id or 0)
    except Exception as exc:
        log.error("Failed to fetch comments, retrying next run: %s", exc)
        return

    if first_run:
        log.info("First run: saved the newest comment, newer ones will be reported from the next check on")
    else:
        log.info("%d new comment(s)", len(result.comments))
        if result.comments:
            title, body = notify.render(env, result, settings.message_format)
            if not notify.send(settings.notify_url.get_secret_value(), title, body, settings.message_format):
                log.error("Failed to send notification, retrying next run")
                return

    state.last_comment_id = max((c.id for c in result.comments), default=state.last_comment_id or 0)


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
