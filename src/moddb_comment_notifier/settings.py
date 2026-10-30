from __future__ import annotations

from pathlib import Path
from typing import Literal

import apprise
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MessageFormat = Literal["markdown", "html", "text"]


class TemplateSettings(BaseSettings):
    """The part of the configuration needed to render messages, e.g. for --preview."""

    model_config = SettingsConfigDict(env_prefix="MCN_", env_file=".env", extra="ignore")

    template_dir: Path | None = None
    message_format: MessageFormat = "markdown"

    @field_validator("message_format", mode="before")
    @classmethod
    def lower_message_format(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    @field_validator("template_dir")
    @classmethod
    def check_template_dir(cls, value: Path | None) -> Path | None:
        if value is not None and not value.is_dir():
            raise ValueError(f"'{value}' is not a directory")
        return value


class Settings(TemplateSettings):
    """All configuration, read from environment variables (prefix MCN_) or a .env file."""

    member: str = Field(min_length=1)
    notify_url: SecretStr
    interval: int = Field(default=30, ge=1)
    moddb_username: str = ""
    moddb_password: SecretStr = SecretStr("")
    state_dir: Path = Path("state")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def upper_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("member")
    @classmethod
    def strip_member(cls, value: str) -> str:
        return value.strip()

    @field_validator("notify_url")
    @classmethod
    def check_notify_url(cls, value: SecretStr) -> SecretStr:
        apobj = apprise.Apprise()
        if not apobj.add(value.get_secret_value()) or len(apobj) != 1:
            raise ValueError("must be exactly one valid Apprise URL, see https://appriseit.com/services/")
        return value

    @property
    def moddb_login_enabled(self) -> bool:
        return bool(self.moddb_username and self.moddb_password.get_secret_value())
