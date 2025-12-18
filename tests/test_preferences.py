"""Unit tests for preferences.py - global user preferences."""

import pytest
import json
from pathlib import Path
from datetime import date

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mind.preferences import (
    DEFAULT_PREFERENCES,
    get_global_mind_dir,
    get_preferences_file,
    get_default_preferences,
    load_global_preferences,
    save_global_preferences,
    has_existing_preferences,
    update_last_project,
    get_logging_level,
    get_auto_promote,
    get_retention_mode,
    merge_with_defaults,
)


class TestGetGlobalMindDir:
    """Tests for get_global_mind_dir function."""

    def test_returns_home_mind_dir(self):
        """Should return ~/.mind path."""
        result = get_global_mind_dir()
        assert result == Path.home() / ".mind"

    def test_returns_pathlib_path(self):
        """Should return a pathlib.Path object."""
        result = get_global_mind_dir()
        assert isinstance(result, Path)


class TestGetPreferencesFile:
    """Tests for get_preferences_file function."""

    def test_returns_preferences_json_path(self):
        """Should return ~/.mind/preferences.json path."""
        result = get_preferences_file()
        assert result == Path.home() / ".mind" / "preferences.json"


class TestGetDefaultPreferences:
    """Tests for get_default_preferences function."""

    def test_returns_copy(self):
        """Should return a copy, not the original."""
        prefs1 = get_default_preferences()
        prefs1["modified"] = True

        prefs2 = get_default_preferences()
        assert "modified" not in prefs2

    def test_has_version(self):
        """Should have version field."""
        prefs = get_default_preferences()
        assert "version" in prefs
        assert prefs["version"] == 1

    def test_has_logging_level(self):
        """Should have logging_level field defaulting to balanced."""
        prefs = get_default_preferences()
        assert prefs["logging_level"] == "balanced"

    def test_has_auto_promote(self):
        """Should have auto_promote field defaulting to True."""
        prefs = get_default_preferences()
        assert prefs["auto_promote"] is True

    def test_has_retention_mode(self):
        """Should have retention_mode field defaulting to smart."""
        prefs = get_default_preferences()
        assert prefs["retention_mode"] == "smart"

    def test_sets_created_date(self):
        """Should set created to today's date."""
        prefs = get_default_preferences()
        assert prefs["created"] == date.today().isoformat()


class TestLoadGlobalPreferences:
    """Tests for load_global_preferences function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_returns_none_when_file_missing(self, temp_home):
        """Should return None when preferences file doesn't exist."""
        result = load_global_preferences()
        assert result is None

    def test_loads_existing_preferences(self, temp_home):
        """Should load preferences from existing file."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text(json.dumps({
            "version": 1,
            "logging_level": "detailed",
            "custom_key": "custom_value"
        }), encoding="utf-8")

        result = load_global_preferences()

        assert result is not None
        assert result["logging_level"] == "detailed"
        assert result["custom_key"] == "custom_value"

    def test_returns_none_for_corrupted_json(self, temp_home):
        """Should return None for invalid JSON."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text("not valid json {{{", encoding="utf-8")

        result = load_global_preferences()

        assert result is None

    def test_returns_none_for_empty_file(self, temp_home):
        """Should return None for empty file."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text("", encoding="utf-8")

        result = load_global_preferences()

        assert result is None


class TestSaveGlobalPreferences:
    """Tests for save_global_preferences function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_creates_mind_dir_if_missing(self, temp_home):
        """Should create ~/.mind directory if it doesn't exist."""
        prefs = {"version": 1, "test": True}

        result = save_global_preferences(prefs)

        assert result is True
        assert (temp_home / ".mind").exists()
        assert (temp_home / ".mind").is_dir()

    def test_creates_preferences_file(self, temp_home):
        """Should create preferences.json file."""
        prefs = {"version": 1, "test": True}

        save_global_preferences(prefs)

        prefs_file = temp_home / ".mind" / "preferences.json"
        assert prefs_file.exists()

    def test_writes_valid_json(self, temp_home):
        """Should write valid JSON."""
        prefs = {"version": 1, "logging_level": "efficient"}

        save_global_preferences(prefs)

        prefs_file = temp_home / ".mind" / "preferences.json"
        loaded = json.loads(prefs_file.read_text(encoding="utf-8"))
        assert loaded["version"] == 1
        assert loaded["logging_level"] == "efficient"

    def test_overwrites_existing(self, temp_home):
        """Should overwrite existing preferences."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text('{"old": "value"}', encoding="utf-8")

        save_global_preferences({"new": "value"})

        loaded = json.loads(prefs_file.read_text(encoding="utf-8"))
        assert "old" not in loaded
        assert loaded["new"] == "value"

    def test_returns_true_on_success(self, temp_home):
        """Should return True on success."""
        result = save_global_preferences({"test": True})
        assert result is True


class TestHasExistingPreferences:
    """Tests for has_existing_preferences function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_returns_false_when_no_prefs(self, temp_home):
        """Should return False when no preferences exist."""
        result = has_existing_preferences()
        assert result is False

    def test_returns_true_when_prefs_exist(self, temp_home):
        """Should return True when preferences exist."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text('{"version": 1}', encoding="utf-8")

        result = has_existing_preferences()

        assert result is True


class TestUpdateLastProject:
    """Tests for update_last_project function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_creates_prefs_if_missing(self, temp_home, tmp_path):
        """Should create preferences if they don't exist."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        update_last_project(project_path)

        prefs = load_global_preferences()
        assert prefs is not None
        assert prefs["last_project"] == str(project_path.resolve())

    def test_updates_existing_prefs(self, temp_home, tmp_path):
        """Should update existing preferences."""
        # Create existing prefs
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text(json.dumps({
            "version": 1,
            "logging_level": "detailed",
            "last_project": "/old/project"
        }), encoding="utf-8")

        project_path = tmp_path / "new-project"
        project_path.mkdir()

        update_last_project(project_path)

        prefs = load_global_preferences()
        assert prefs["logging_level"] == "detailed"  # Preserved
        assert prefs["last_project"] == str(project_path.resolve())  # Updated


class TestGetLoggingLevel:
    """Tests for get_logging_level function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_returns_default_when_no_prefs(self, temp_home):
        """Should return 'balanced' when no preferences exist."""
        result = get_logging_level()
        assert result == "balanced"

    def test_returns_configured_level(self, temp_home):
        """Should return configured logging level."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text('{"logging_level": "efficient"}', encoding="utf-8")

        result = get_logging_level()

        assert result == "efficient"


class TestGetAutoPromote:
    """Tests for get_auto_promote function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_returns_default_when_no_prefs(self, temp_home):
        """Should return True when no preferences exist."""
        result = get_auto_promote()
        assert result is True

    def test_returns_configured_value(self, temp_home):
        """Should return configured auto_promote value."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text('{"auto_promote": false}', encoding="utf-8")

        result = get_auto_promote()

        assert result is False


class TestGetRetentionMode:
    """Tests for get_retention_mode function."""

    @pytest.fixture
    def temp_home(self, tmp_path, monkeypatch):
        """Create temporary home directory."""
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        return tmp_path

    def test_returns_default_when_no_prefs(self, temp_home):
        """Should return 'smart' when no preferences exist."""
        result = get_retention_mode()
        assert result == "smart"

    def test_returns_configured_mode(self, temp_home):
        """Should return configured retention mode."""
        mind_dir = temp_home / ".mind"
        mind_dir.mkdir()
        prefs_file = mind_dir / "preferences.json"
        prefs_file.write_text('{"retention_mode": "keep_all"}', encoding="utf-8")

        result = get_retention_mode()

        assert result == "keep_all"


class TestMergeWithDefaults:
    """Tests for merge_with_defaults function."""

    def test_fills_missing_fields(self):
        """Should fill in missing fields from defaults."""
        partial = {"logging_level": "efficient"}

        result = merge_with_defaults(partial)

        assert result["logging_level"] == "efficient"
        assert result["auto_promote"] is True  # From defaults
        assert result["retention_mode"] == "smart"  # From defaults
        assert result["version"] == 1  # From defaults

    def test_preserves_user_values(self):
        """Should preserve user-provided values."""
        user_prefs = {
            "logging_level": "detailed",
            "auto_promote": False,
            "retention_mode": "keep_all",
        }

        result = merge_with_defaults(user_prefs)

        assert result["logging_level"] == "detailed"
        assert result["auto_promote"] is False
        assert result["retention_mode"] == "keep_all"

    def test_handles_empty_dict(self):
        """Should return defaults for empty dict."""
        result = merge_with_defaults({})

        assert result["logging_level"] == "balanced"
        assert result["auto_promote"] is True
        assert result["retention_mode"] == "smart"

    def test_ignores_none_values(self):
        """Should ignore None values and use defaults."""
        partial = {"logging_level": None}

        result = merge_with_defaults(partial)

        # None should be ignored, default used
        assert result["logging_level"] == "balanced"
