"""Tests for CGCPT-Server configuration module."""

import os
import importlib
import pytest


class TestDefaultConfig:
    def test_default_secret_key(self):
        """Default SECRET_KEY should be 'change-me-in-production'."""
        # Remove env var to test default
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("SECRET_KEY", raising=False)
            import config
            importlib.reload(config)
            assert config.SECRET_KEY == "change-me-in-production"

    def test_default_admin_user(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("ADMIN_USER", raising=False)
            import config
            importlib.reload(config)
            assert config.ADMIN_USER == "admin"

    def test_default_admin_pass(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("ADMIN_PASS", raising=False)
            import config
            importlib.reload(config)
            assert config.ADMIN_PASS == "123"

    def test_default_host(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("HOST", raising=False)
            import config
            importlib.reload(config)
            assert config.HOST == "0.0.0.0"

    def test_default_port(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("PORT", raising=False)
            import config
            importlib.reload(config)
            assert config.PORT == 5000

    def test_default_debug(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("DEBUG", raising=False)
            import config
            importlib.reload(config)
            assert isinstance(config.DEBUG, bool)

    def test_default_database_url(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("CGCPT_DB_URL", raising=False)
            import config
            importlib.reload(config)
            assert "mysql" in config.DATABASE_URL

    def test_default_log_level(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("LOG_LEVEL", raising=False)
            import config
            importlib.reload(config)
            assert config.LOG_LEVEL == "INFO"

    def test_database_dir_is_path(self):
        import config
        importlib.reload(config)
        from pathlib import Path
        assert isinstance(config.DATABASE_DIR, Path)


class TestEnvOverride:
    def test_secret_key_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("SECRET_KEY", "my-test-secret")
            import config
            importlib.reload(config)
            assert config.SECRET_KEY == "my-test-secret"

    def test_admin_user_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("ADMIN_USER", "superadmin")
            import config
            importlib.reload(config)
            assert config.ADMIN_USER == "superadmin"

    def test_admin_pass_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("ADMIN_PASS", "strongpass")
            import config
            importlib.reload(config)
            assert config.ADMIN_PASS == "strongpass"

    def test_host_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("HOST", "127.0.0.1")
            import config
            importlib.reload(config)
            assert config.HOST == "127.0.0.1"

    def test_port_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("PORT", "8080")
            import config
            importlib.reload(config)
            assert config.PORT == 8080

    def test_debug_false_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("DEBUG", "false")
            import config
            importlib.reload(config)
            assert config.DEBUG is False

    def test_database_url_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("CGCPT_DB_URL", "sqlite:///test.db")
            import config
            importlib.reload(config)
            assert config.DATABASE_URL == "sqlite:///test.db"

    def test_log_level_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("LOG_LEVEL", "DEBUG")
            import config
            importlib.reload(config)
            assert config.LOG_LEVEL == "DEBUG"

    def test_cors_origins_override(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("CORS_ORIGINS", "http://localhost:3000,http://example.com")
            import config
            importlib.reload(config)
            assert "localhost:3000" in config.CORS_ORIGINS
