from __future__ import annotations

import os
import tomllib
from pathlib import Path

from .models import Member, Settings

CONFIG_FILE_NAME = "config.toml"
TEMPLATE_FILE_NAME = "template.txt"
LAST_CHECKED_FILE_NAME = "last_update.txt"
SESSION_DATA_FILE_NAME = "session_data.txt"
CONFIG_DIR_ENV_VAR = "MCN_CONFIG_DIR"
STATE_DIR_ENV_VAR = "MCN_STATE_DIR"


def resolve_config_dir() -> Path:
    env_dir = os.getenv(CONFIG_DIR_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.cwd()


def resolve_state_dir() -> Path:
    env_dir = os.getenv(STATE_DIR_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.cwd()


def load_settings() -> Settings:
    config_dir = resolve_config_dir()
    state_dir = resolve_state_dir()
    config_file = config_dir / CONFIG_FILE_NAME
    template_file = config_dir / TEMPLATE_FILE_NAME
    last_checked_file = state_dir / LAST_CHECKED_FILE_NAME
    session_data_file = state_dir / SESSION_DATA_FILE_NAME

    if not config_file.exists():
        raise FileNotFoundError(f"Missing {CONFIG_FILE_NAME} at: {config_file}")

    if not template_file.exists():
        raise FileNotFoundError(f"Missing {TEMPLATE_FILE_NAME} at: {template_file}")

    config = tomllib.loads(config_file.read_text(encoding="utf-8"))
    members = [Member(**member) for member in config["members"]["uids"]]

    moddb_config = config.get("moddb", {})
    return Settings(
        schedule_interval=config["schedule"]["interval"],
        smtp_server=config["smtp"]["server"],
        smtp_port=config["smtp"]["port"],
        email=config["smtp"]["email"],
        email_password=config["smtp"]["password"],
        email_subject=config["email"]["subject"],
        email_sender=config["email"]["sender"],
        moddb_username=moddb_config.get("username", ""),
        moddb_password=moddb_config.get("password", ""),
        members=members,
        email_template=template_file.read_text(encoding="utf-8"),
        last_checked_file=last_checked_file,
        session_data_file=session_data_file,
    )


def get_last_checked(settings: Settings) -> int:
    try:
        return int(settings.last_checked_file.read_text(encoding="utf-8").strip())
    except Exception:
        return 0


def save_last_checked(settings: Settings, timestamp: int) -> None:
    settings.last_checked_file.parent.mkdir(parents=True, exist_ok=True)
    settings.last_checked_file.write_text(f"{timestamp}\n", encoding="utf-8")


def read_session_cookie(settings: Settings) -> str | None:
    try:
        value = settings.session_data_file.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    return value or None


def write_session_cookie(settings: Settings, cookie: str) -> None:
    settings.session_data_file.parent.mkdir(parents=True, exist_ok=True)
    settings.session_data_file.write_text(cookie.strip(), encoding="utf-8")


def delete_session_cookie(settings: Settings) -> bool:
    try:
        settings.session_data_file.unlink()
        return True
    except FileNotFoundError:
        return False
    except Exception as exc:
        print(f"Failed to delete stale session cookie file: {exc}")
        return False
