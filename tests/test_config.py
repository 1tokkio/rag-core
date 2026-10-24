from app.core.config import Settings


def test_defaults_do_not_require_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key is None
    assert settings.llm_model == "claude-haiku-5-5"
    assert settings.embedding_model == "intfloat/multilingual-e5-small"


def test_values_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/x"
    assert settings.log_level == "debug"


def test_api_key_is_not_leaked_in_repr(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-secret-value")

    settings = Settings(_env_file=None)

    assert "sk-test-secret-value" not in repr(settings)
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-test-secret-value"
