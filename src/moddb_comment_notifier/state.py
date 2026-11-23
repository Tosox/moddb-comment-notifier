from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)

STATE_FILE_NAME = "state.json"


@dataclass
class State:
    """Persisted between runs: the newest comment ID already handled and the ModDB session cookie."""

    last_comment_id: int | None = None
    session_cookie: str | None = None

    @classmethod
    def load(cls, state_dir: Path) -> State:
        path = state_dir / STATE_FILE_NAME
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            last_comment_id = data.get("last_comment_id")
            return cls(
                last_comment_id=int(last_comment_id) if last_comment_id is not None else None,
                session_cookie=data.get("session_cookie"),
            )
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.warning("Ignoring unreadable state file %s: %s", path, exc)
            return cls()

    def save(self, state_dir: Path) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / STATE_FILE_NAME
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
