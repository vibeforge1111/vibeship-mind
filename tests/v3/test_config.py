"""Tests for unified v3 configuration."""
import tempfile
from pathlib import Path

import pytest

from mind.v3.config import V3Settings, get_settings, reset_settings


class TestV3Settings:
    """Tests for V3Settings."""

    def test_default_settings(self):
        settings = V3Settings()
        assert settings.enabled is True
        assert settings.debug is False

    def test_decay_defaults(self):
        settings = V3Settings()
        assert settings.decay.half_life_hours == 48

    def test_embeddings_defaults(self):
        settings = V3Settings()
        assert settings.embeddings.model_name == "all-MiniLM-L6-v2"
        assert settings.embeddings.use_gpu is False

    def test_from_dict(self):
        data = {
            "enabled": False,
            "debug": True,
            "decay": {"half_life_hours": 24},
        }
        settings = V3Settings.from_dict(data)

        assert settings.enabled is False
        assert settings.debug is True
        assert settings.decay.half_life_hours == 24

    def test_from_dict_partial(self):
        data = {"debug": True}
        settings = V3Settings.from_dict(data)

        assert settings.debug is True
        assert settings.enabled is True  # Default preserved

    def test_to_dict(self):
        settings = V3Settings()
        data = settings.to_dict()

        assert "enabled" in data
        assert "decay" in data
        assert "embeddings" in data


class TestV3SettingsFile:
    """Tests for file-based configuration."""

    def test_from_nonexistent_file(self):
        settings = V3Settings.from_file(Path("/nonexistent/v3.toml"))
        assert settings.enabled is True  # Defaults

    def test_from_toml_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "v3.toml"
            config_file.write_text("""
enabled = false
debug = true

[decay]
half_life_hours = 72

[embeddings]
use_gpu = true
""")
            settings = V3Settings.from_file(config_file)

            assert settings.enabled is False
            assert settings.debug is True
            assert settings.decay.half_life_hours == 72
            assert settings.embeddings.use_gpu is True

    def test_from_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            mind_dir = project_path / ".mind"
            mind_dir.mkdir()

            config_file = mind_dir / "v3.toml"
            config_file.write_text("""
[watcher]
enabled = false
""")
            settings = V3Settings.from_project(project_path)

            assert settings.watcher.enabled is False


class TestGetSettings:
    """Tests for get_settings function."""

    def setup_method(self):
        reset_settings()

    def teardown_method(self):
        reset_settings()

    def test_get_default_settings(self):
        settings = get_settings()
        assert settings.enabled is True

    def test_get_settings_singleton(self):
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_with_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = get_settings(Path(tmpdir))
            assert settings is not None
