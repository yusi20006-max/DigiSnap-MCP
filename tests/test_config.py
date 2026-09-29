import pytest

from digisnap_mcp.config import Settings


def test_default_settings() -> None:
    settings = Settings.from_env()
    assert settings.request_timeout_seconds > 0
    assert settings.max_results >= 1


def test_invalid_timeout(monkeypatch) -> None:
    monkeypatch.setenv("DIGISNAP_TIMEOUT", "0")
    with pytest.raises(ValueError, match="positive"):
        Settings.from_env()
