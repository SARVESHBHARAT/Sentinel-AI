from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    demo_mode: bool
    openai_model: str
    openai_api_key: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        return cls(
            database_path=Path(os.getenv("SENTINEL_DATABASE_PATH", "data/sentinel.db")),
            demo_mode=_as_bool(os.getenv("SENTINEL_DEMO_MODE"), default=True),
            openai_model=os.getenv("SENTINEL_OPENAI_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        )

    @property
    def effective_demo_mode(self) -> bool:
        """Demo mode is mandatory if no API key is configured."""
        return self.demo_mode or self.openai_api_key is None
