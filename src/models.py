from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Member:
    uid: str
    email: str


@dataclass(frozen=True)
class Settings:
    schedule_interval: int
    smtp_server: str
    smtp_port: int
    email: str
    email_password: str
    email_subject: str
    email_sender: str
    moddb_username: str
    moddb_password: str
    members: list[Member]
    email_template: str
    last_checked_file: Path
