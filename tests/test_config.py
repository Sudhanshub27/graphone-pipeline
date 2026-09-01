from config.settings import settings


def test_default_config_settings():
    assert settings.MAX_CONCURRENT_SCRAPES == 20
    assert settings.MAX_CONCURRENT_LLM_CALLS == 3
    assert settings.RATE_LIMIT_PER_MINUTE == 60
    assert settings.HTTP_TIMEOUT_SECONDS == 30
    assert settings.LOG_LEVEL == "INFO"
    assert settings.DATA_RAW_DIR.name == "raw"
    assert settings.DATA_PROCESSED_DIR.name == "processed"
    assert settings.LOGS_DIR.name == "logs"
