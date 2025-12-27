"""Unit tests for config.py - project configuration handling."""

import pytest
import json
from pathlib import Path

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.config import (
    DEFAULT_CONFIG,
    get_config_file,
    load_config,
    save_config,
    is_feature_enabled,
    is_self_improve_feature_enabled,
    enable_feature,
    disable_feature,
    is_mascot_enabled,
    set_mascot_enabled,
    create_default_config,
)


class TestGetConfigFile:
    """Tests for get_config_file function."""

    def test_returns_correct_path(self, tmp_path):
        """Should return path to config.json in .mind directory."""
        config_path = get_config_file(tmp_path)

        assert config_path == tmp_path / ".mind" / "config.json"

    def test_returns_pathlib_path(self, tmp_path):
        """Should return a pathlib.Path object."""
        config_path = get_config_file(tmp_path)

        assert isinstance(config_path, Path)


class TestLoadConfig:
    """Tests for load_config function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_load_missing_file_returns_defaults(self, temp_project):
        """Should return default config when file doesn't exist."""
        config = load_config(temp_project)

        assert config == DEFAULT_CONFIG

    def test_load_existing_config(self, temp_project):
        """Should load config from existing file."""
        config_file = temp_project / ".mind" / "config.json"
        custom_config = {
            "version": 2,
            "mascot": False,
            "custom_key": "custom_value"
        }
        config_file.write_text(json.dumps(custom_config), encoding="utf-8")

        config = load_config(temp_project)

        assert config["version"] == 2
        assert config["mascot"] is False
        assert config["custom_key"] == "custom_value"

    def test_load_corrupted_json_returns_defaults(self, temp_project):
        """Should return defaults when JSON is invalid."""
        config_file = temp_project / ".mind" / "config.json"
        config_file.write_text("not valid json {{{", encoding="utf-8")

        config = load_config(temp_project)

        assert config == DEFAULT_CONFIG

    def test_load_empty_file_returns_defaults(self, temp_project):
        """Should return defaults when file is empty."""
        config_file = temp_project / ".mind" / "config.json"
        config_file.write_text("", encoding="utf-8")

        config = load_config(temp_project)

        assert config == DEFAULT_CONFIG

    def test_load_returns_copy_of_defaults(self, temp_project):
        """Should return a copy, not the original DEFAULT_CONFIG."""
        config1 = load_config(temp_project)
        config1["modified"] = True

        config2 = load_config(temp_project)

        assert "modified" not in config2
        assert "modified" not in DEFAULT_CONFIG


class TestSaveConfig:
    """Tests for save_config function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_save_creates_file(self, temp_project):
        """Should create config.json file."""
        config = {"version": 1, "test": True}

        save_config(temp_project, config)

        config_file = temp_project / ".mind" / "config.json"
        assert config_file.exists()

    def test_save_writes_json(self, temp_project):
        """Should write valid JSON."""
        config = {"version": 1, "test": True}

        save_config(temp_project, config)

        config_file = temp_project / ".mind" / "config.json"
        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        assert loaded["version"] == 1
        assert loaded["test"] is True

    def test_save_overwrites_existing(self, temp_project):
        """Should overwrite existing config file."""
        config_file = temp_project / ".mind" / "config.json"
        config_file.write_text('{"old": "config"}', encoding="utf-8")

        save_config(temp_project, {"new": "config"})

        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        assert "old" not in loaded
        assert loaded["new"] == "config"

    def test_save_formats_with_indent(self, temp_project):
        """Should format JSON with indentation for readability."""
        config = {"version": 1, "nested": {"key": "value"}}

        save_config(temp_project, config)

        config_file = temp_project / ".mind" / "config.json"
        content = config_file.read_text(encoding="utf-8")
        # Check for newlines and indentation
        assert "\n" in content
        assert "  " in content


class TestIsFeatureEnabled:
    """Tests for is_feature_enabled function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_disabled_by_default(self, temp_project):
        """Should return False for unknown features."""
        result = is_feature_enabled("unknown_feature", temp_project)

        assert result is False

    def test_enabled_feature(self, temp_project):
        """Should return True for enabled feature."""
        config_file = temp_project / ".mind" / "config.json"
        config = {
            "experimental": {
                "my_feature": True
            }
        }
        config_file.write_text(json.dumps(config), encoding="utf-8")

        result = is_feature_enabled("my_feature", temp_project)

        assert result is True

    def test_disabled_feature(self, temp_project):
        """Should return False for explicitly disabled feature."""
        config_file = temp_project / ".mind" / "config.json"
        config = {
            "experimental": {
                "my_feature": False
            }
        }
        config_file.write_text(json.dumps(config), encoding="utf-8")

        result = is_feature_enabled("my_feature", temp_project)

        assert result is False


class TestIsSelfImproveFeatureEnabled:
    """Tests for is_self_improve_feature_enabled function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_default_features_enabled(self, temp_project):
        """Self-improvement features should be enabled by default."""
        assert is_self_improve_feature_enabled("enabled", temp_project) is True
        assert is_self_improve_feature_enabled("decay", temp_project) is True
        assert is_self_improve_feature_enabled("reinforcement", temp_project) is True
        assert is_self_improve_feature_enabled("contradiction", temp_project) is True
        assert is_self_improve_feature_enabled("learning_style", temp_project) is True

    def test_unknown_feature_disabled(self, temp_project):
        """Unknown self-improvement features should be disabled."""
        result = is_self_improve_feature_enabled("unknown_feature", temp_project)

        assert result is False

    def test_explicitly_disabled_feature(self, temp_project):
        """Should respect explicitly disabled features."""
        config_file = temp_project / ".mind" / "config.json"
        config = {
            "self_improve": {
                "enabled": True,
                "decay": False,  # Explicitly disabled
            }
        }
        config_file.write_text(json.dumps(config), encoding="utf-8")

        assert is_self_improve_feature_enabled("enabled", temp_project) is True
        assert is_self_improve_feature_enabled("decay", temp_project) is False


class TestEnableDisableFeature:
    """Tests for enable_feature and disable_feature functions."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_enable_feature(self, temp_project):
        """Should enable a feature."""
        enable_feature("my_feature", temp_project)

        assert is_feature_enabled("my_feature", temp_project) is True

    def test_disable_feature(self, temp_project):
        """Should disable a feature."""
        enable_feature("my_feature", temp_project)
        disable_feature("my_feature", temp_project)

        assert is_feature_enabled("my_feature", temp_project) is False

    def test_enable_creates_experimental_section(self, temp_project):
        """Should create experimental section if missing."""
        config_file = temp_project / ".mind" / "config.json"
        config_file.write_text('{"version": 1}', encoding="utf-8")

        enable_feature("new_feature", temp_project)

        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        assert "experimental" in loaded
        assert loaded["experimental"]["new_feature"] is True


class TestMascotSettings:
    """Tests for mascot enable/disable functions."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_mascot_enabled_by_default(self, temp_project):
        """Mascot should be enabled by default."""
        result = is_mascot_enabled(temp_project)

        assert result is True

    def test_disable_mascot(self, temp_project):
        """Should disable mascot."""
        set_mascot_enabled(temp_project, False)

        assert is_mascot_enabled(temp_project) is False

    def test_enable_mascot(self, temp_project):
        """Should enable mascot."""
        set_mascot_enabled(temp_project, False)
        set_mascot_enabled(temp_project, True)

        assert is_mascot_enabled(temp_project) is True


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .mind directory."""
        mind_dir = tmp_path / ".mind"
        mind_dir.mkdir()
        return tmp_path

    def test_creates_config_file(self, temp_project):
        """Should create config.json with defaults."""
        config_file = temp_project / ".mind" / "config.json"
        assert not config_file.exists()

        create_default_config(temp_project)

        assert config_file.exists()
        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        assert loaded["version"] == DEFAULT_CONFIG["version"]
        assert loaded["mascot"] == DEFAULT_CONFIG["mascot"]

    def test_does_not_overwrite_existing(self, temp_project):
        """Should not overwrite existing config file."""
        config_file = temp_project / ".mind" / "config.json"
        custom = {"custom": "value", "version": 99}
        config_file.write_text(json.dumps(custom), encoding="utf-8")

        create_default_config(temp_project)

        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        assert loaded["custom"] == "value"
        assert loaded["version"] == 99


class TestDefaultConfig:
    """Tests for DEFAULT_CONFIG structure."""

    def test_has_version(self):
        """DEFAULT_CONFIG should have a version."""
        assert "version" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["version"], int)

    def test_has_mascot(self):
        """DEFAULT_CONFIG should have mascot setting."""
        assert "mascot" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["mascot"], bool)

    def test_has_self_improve(self):
        """DEFAULT_CONFIG should have self_improve section."""
        assert "self_improve" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["self_improve"], dict)

    def test_self_improve_has_all_features(self):
        """self_improve should have all expected features."""
        si = DEFAULT_CONFIG["self_improve"]
        assert "enabled" in si
        assert "decay" in si
        assert "reinforcement" in si
        assert "contradiction" in si
        assert "learning_style" in si

    def test_has_experimental(self):
        """DEFAULT_CONFIG should have experimental section."""
        assert "experimental" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["experimental"], dict)
