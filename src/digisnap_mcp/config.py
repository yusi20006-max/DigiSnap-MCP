"""Environment-backed configuration."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    log_level: str = "INFO"
    request_timeout_seconds: float = 15.0
    max_results: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        timeout = float(os.getenv("DIGISNAP_TIMEOUT", "15"))
        max_results = int(os.getenv("DIGISNAP_MAX_RESULTS", "20"))
        if timeout <= 0:
            raise ValueError("DIGISNAP_TIMEOUT must be positive")
        if max_results < 1:
            raise ValueError("DIGISNAP_MAX_RESULTS must be at least 1")
        return cls(
            log_level=os.getenv("DIGISNAP_LOG_LEVEL", "INFO"),
            request_timeout_seconds=timeout,
            max_results=max_results,
        )
