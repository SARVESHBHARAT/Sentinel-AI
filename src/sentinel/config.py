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
    openai_model_version_override: str | None = None
    model_intelligence_min_sample: int = 5
    read_only: bool = False
    submission_rate_limit: int = 20
    submission_rate_window_seconds: int = 3600

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        raw_min = (os.getenv("SENTINEL_MODEL_INTEL_MIN_SAMPLE") or "").strip()
        try:
            min_sample = int(raw_min) if raw_min else 5
        except ValueError:
            min_sample = 5
        raw_limit = (os.getenv("SENTINEL_SUBMISSION_RATE_LIMIT") or "").strip()
        try:
            rate_limit = int(raw_limit) if raw_limit else 20
        except ValueError:
            rate_limit = 20
        raw_window = (os.getenv("SENTINEL_SUBMISSION_RATE_WINDOW") or "").strip()
        try:
            rate_window = int(raw_window) if raw_window else 3600
        except ValueError:
            rate_window = 3600
        return cls(
            database_path=Path(os.getenv("SENTINEL_DATABASE_PATH", "data/sentinel.db")),
            demo_mode=_as_bool(os.getenv("SENTINEL_DEMO_MODE"), default=True),
            openai_model=os.getenv("SENTINEL_OPENAI_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model_version_override=os.getenv("SENTINEL_OPENAI_MODEL_VERSION") or None,
            model_intelligence_min_sample=max(1, min_sample),
            read_only=_as_bool(os.getenv("SENTINEL_READ_ONLY"), default=False),
            submission_rate_limit=max(1, rate_limit),
            submission_rate_window_seconds=max(60, rate_window),
        )

    @property
    def effective_demo_mode(self) -> bool:
        """Demo mode is mandatory if no API key is configured."""
        return self.demo_mode or self.openai_api_key is None
