"""Unit tests for MCP configuration checking in cli.py."""

import json
import os
import sys
from pathlib import Path

import pytest

from mind.cli import (
    get_claude_config_paths,
    get_cursor_config_paths,
    get_all_mcp_config_paths,
    get_mind_project_root,
    check_mcp_configuration,
    ensure_mcp_configuration,
)


class TestGetClaudeConfigPaths:
    """Tests for get_claude_config_paths() function."""

    def test_macos_linux_path(self, monkeypatch):
        """Should return Mac/Linux config path for non-Windows platforms."""
        monkeypatch.setattr("mind.cli.sys.platform", "darwin")
        paths = get_claude_config_paths()
        
        assert len(paths) == 1
        assert paths[0] == Path.home() / ".config" / "claude" / "mcp.json"

    def test_windows_path(self, monkeypatch):
        """Should return Windows config path."""
        monkeypatch.setattr("mind.cli.sys.platform", "win32")
        monkeypatch.setenv("APPDATA", "C:\\Users\\Test\\AppData\\Roaming")
        paths = get_claude_config_paths()
        
        assert len(paths) == 1
        assert paths[0] == Path("C:\\Users\\Test\\AppData\\Roaming") / "Claude" / "claude_desktop_config.json"


class TestGetCursorConfigPaths:
    """Tests for get_cursor_config_paths() function."""

    def test_macos_linux_path(self, monkeypatch):
        """Should return Mac/Linux config path for non-Windows platforms."""
        monkeypatch.setattr("mind.cli.sys.platform", "darwin")
        paths = get_cursor_config_paths()
        
        assert len(paths) == 1
        assert paths[0] == Path.home() / ".cursor" / "mcp.json"

    def test_windows_path(self, monkeypatch):
        """Should return Windows config path."""
        monkeypatch.setattr("mind.cli.sys.platform", "win32")
        monkeypatch.setenv("APPDATA", "C:\\Users\\Test\\AppData\\Roaming")
        paths = get_cursor_config_paths()
        
        assert len(paths) == 1
        assert paths[0] == Path("C:\\Users\\Test\\AppData\\Roaming") / "Cursor" / "mcp.json"


class TestGetAllMcpConfigPaths:
    """Tests for get_all_mcp_config_paths() function."""

    def test_returns_both_claude_and_cursor(self, monkeypatch):
        """Should return both Claude and Cursor config paths."""
        monkeypatch.setattr("mind.cli.sys.platform", "darwin")
        paths = get_all_mcp_config_paths()
        
        assert len(paths) == 2
        assert any("claude" in str(p).lower() for p in paths)
        assert any("cursor" in str(p).lower() for p in paths)


class TestGetMindProjectRoot:
    """Tests for get_mind_project_root() function."""

    def test_finds_root_from_package_location(self, tmp_path, monkeypatch):
        """Should find project root when running from package location."""
        project_root = tmp_path / "vibeship-mind"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'mind-memory'")
        (project_root / "src" / "mind").mkdir(parents=True)
        (project_root / "src" / "mind" / "cli.py").write_text("# mock")
        
        monkeypatch.setattr("mind.cli.__file__", str(project_root / "src" / "mind" / "cli.py"))
        root = get_mind_project_root()
        assert root == project_root.resolve()

    def test_returns_none_when_not_found(self, monkeypatch):
        """Should return None when project root cannot be found."""
        monkeypatch.setattr("mind.cli.__file__", "/some/random/path/cli.py")
        monkeypatch.setattr("mind.cli.Path.cwd", lambda: Path("/tmp"))
        root = get_mind_project_root()
        assert root is None


class TestCheckMcpConfiguration:
    """Tests for check_mcp_configuration() function."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        project_root = tmp_path / "vibeship-mind"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'mind-memory'")
        (project_root / "src" / "mind").mkdir(parents=True)
        return project_root.resolve()

    def test_config_file_not_found(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when config file doesn't exist."""
        config_path = temp_config_dir / "mcp.json"
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "not found" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_mind_server_not_configured(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when mind server is not in config."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "other_server": {
                    "command": "uv",
                    "args": ["run", "other"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "mind" in status.lower() and "not found" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_missing_directory_arg(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when --directory argument is missing."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "--directory" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_wrong_directory_path(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when directory path doesn't match."""
        config_path = temp_config_dir / "mcp.json"
        wrong_path = "/wrong/path/to/vibeship-mind"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", wrong_path, "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "mismatch" in status.lower() or "path" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_wrong_command(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when command is not 'uv'."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "python",
                    "args": ["--directory", str(mock_project_root), "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "uv" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_missing_required_args(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when required args (run, mind, mcp) are missing."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", str(mock_project_root)]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "run" in status.lower() or "mind" in status.lower() or "mcp" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_correct_configuration(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return True when configuration is correct."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", str(mock_project_root), "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is True
        assert "correctly" in status.lower() or "configured" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_invalid_json(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should return False when config file has invalid JSON."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text("not valid json {{{", encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "json" in status.lower() or "invalid" in status.lower()
        assert expected_path == str(mock_project_root)

    def test_project_root_not_found(self, temp_config_dir, monkeypatch):
        """Should return False when project root cannot be determined."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", "/some/path", "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: None)
        is_configured, status, expected_path = check_mcp_configuration()
        
        assert is_configured is False
        assert "project root" in status.lower()
        assert expected_path is None


class TestEnsureMcpConfiguration:
    """Tests for ensure_mcp_configuration() function."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        project_root = tmp_path / "vibeship-mind"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'mind-memory'")
        (project_root / "src" / "mind").mkdir(parents=True)
        return project_root.resolve()

    def test_creates_new_config_file(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should create new config file if it doesn't exist."""
        config_path = temp_config_dir / "mcp.json"
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        assert config_path.exists()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "mcpServers" in config
        assert "mind" in config["mcpServers"]
        assert config["mcpServers"]["mind"]["command"] == "uv"
        assert str(mock_project_root) in config["mcpServers"]["mind"]["args"]

    def test_adds_mind_server_to_existing_config(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should add mind server to existing config without mind server."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "other_server": {
                    "command": "python",
                    "args": ["run", "other"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "other_server" in config["mcpServers"]
        assert "mind" in config["mcpServers"]
        assert config["mcpServers"]["mind"]["command"] == "uv"

    def test_updates_wrong_path(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should update config when path is wrong."""
        config_path = temp_config_dir / "mcp.json"
        wrong_path = "/wrong/path/to/vibeship-mind"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", wrong_path, "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        config = json.loads(config_path.read_text(encoding="utf-8"))
        args = config["mcpServers"]["mind"]["args"]
        directory_idx = args.index("--directory")
        assert args[directory_idx + 1] == str(mock_project_root)

    def test_updates_wrong_command(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should update config when command is wrong."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "python",
                    "args": ["--directory", str(mock_project_root), "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert config["mcpServers"]["mind"]["command"] == "uv"

    def test_handles_invalid_json(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should handle invalid JSON by creating new config."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text("not valid json {{{", encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "mcpServers" in config
        assert "mind" in config["mcpServers"]

    def test_returns_false_when_project_root_not_found(self, temp_config_dir, monkeypatch):
        """Should return False when project root cannot be determined."""
        config_path = temp_config_dir / "mcp.json"
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: None)
        
        success, status = ensure_mcp_configuration()
        
        assert success is False
        assert "project root" in status.lower()

    def test_preserves_other_servers(self, temp_config_dir, mock_project_root, monkeypatch):
        """Should preserve other MCP servers when updating."""
        config_path = temp_config_dir / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "other1": {"command": "python", "args": ["run", "other1"]},
                "mind": {
                    "command": "uv",
                    "args": ["--directory", "/wrong/path", "run", "mind", "mcp"]
                },
                "other2": {"command": "node", "args": ["run", "other2"]}
            },
            "otherKey": "otherValue"
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "other1" in config["mcpServers"]
        assert "other2" in config["mcpServers"]
        assert config["otherKey"] == "otherValue"
        assert config["mcpServers"]["mind"]["args"][1] == str(mock_project_root)

    def test_updates_both_claude_and_cursor(self, tmp_path, mock_project_root, monkeypatch):
        """Should update both Claude and Cursor configs."""
        claude_config = tmp_path / "claude_mcp.json"
        cursor_config = tmp_path / "cursor_mcp.json"
        
        # Create both configs with wrong paths
        claude_config.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", "/wrong/path", "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        cursor_config.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", "/wrong/path", "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [claude_config, cursor_config])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        assert success is True
        # Check both configs were updated
        claude_data = json.loads(claude_config.read_text(encoding="utf-8"))
        cursor_data = json.loads(cursor_config.read_text(encoding="utf-8"))
        assert claude_data["mcpServers"]["mind"]["args"][1] == str(mock_project_root)
        assert cursor_data["mcpServers"]["mind"]["args"][1] == str(mock_project_root)

    def test_returns_false_on_partial_success(self, tmp_path, mock_project_root, monkeypatch):
        """Should return False when one config succeeds and another fails."""
        claude_config = tmp_path / "claude_mcp.json"
        cursor_config = tmp_path / "cursor_mcp.json"
        
        # Create one valid config
        claude_config.write_text(json.dumps({
            "mcpServers": {
                "mind": {
                    "command": "uv",
                    "args": ["--directory", "/wrong/path", "run", "mind", "mcp"]
                }
            }
        }), encoding="utf-8")
        
        # Create a directory with the same name as the config file to make it unwritable
        cursor_config.mkdir(parents=True)
        
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [claude_config, cursor_config])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        # Should return False because one config failed
        assert success is False
        assert "Partially updated" in status
        assert "claude_mcp.json" in status
        assert "cursor_mcp.json" in status or "error" in status.lower()
        # Verify the successful config was actually updated
        claude_data = json.loads(claude_config.read_text(encoding="utf-8"))
        assert claude_data["mcpServers"]["mind"]["args"][1] == str(mock_project_root)

    def test_restores_from_memory_when_backup_fails(self, tmp_path, mock_project_root, monkeypatch):
        """Should restore original content from memory when backup creation fails and write fails."""
        config_path = tmp_path / "mcp.json"
        original_config = {
            "mcpServers": {
                "other_server": {"command": "python", "args": ["run", "other"]}
            },
            "otherKey": "originalValue"
        }
        original_content = json.dumps(original_config, indent=2)
        config_path.write_text(original_content, encoding="utf-8")
        
        # Create a wrapper to track calls and make operations fail
        call_count = {"rename": 0, "write": 0}
        original_rename = Path.rename
        original_write_text = Path.write_text
        
        def failing_rename(self, target):
            call_count["rename"] += 1
            if self == config_path:
                raise PermissionError("Cannot create backup")
            return original_rename(self, target)
        
        def failing_write_text(self, data, encoding=None):
            call_count["write"] += 1
            if self == config_path:
                raise IOError("Write failed")
            return original_write_text(self, data, encoding=encoding)
        
        monkeypatch.setattr(Path, "rename", failing_rename)
        monkeypatch.setattr(Path, "write_text", failing_write_text)
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        # Should return False because write failed
        assert success is False
        assert "error" in status.lower() or "failed" in status.lower()
        
        # Verify backup creation was attempted and failed
        assert call_count["rename"] > 0
        
        # Verify write was attempted
        assert call_count["write"] > 0
        
        # Verify original content was restored from memory
        restored_content = config_path.read_text(encoding="utf-8")
        restored_config = json.loads(restored_content)
        assert restored_config == original_config
        assert "otherKey" in restored_config
        assert restored_config["otherKey"] == "originalValue"

    def test_does_not_restore_invalid_json_on_write_failure(self, tmp_path, mock_project_root, monkeypatch):
        """Should not restore invalid JSON when write fails - we were fixing it, not preserving it."""
        config_path = tmp_path / "mcp.json"
        invalid_json_content = "not valid json {{{"
        config_path.write_text(invalid_json_content, encoding="utf-8")
        
        # Track if restore was attempted (by checking if original_content would be written back)
        restore_attempted = []
        original_write_text = Path.write_text
        
        def track_restore_write(self, data, encoding=None):
            # Check if this is a restore attempt (writing back invalid JSON)
            if self == config_path and data == invalid_json_content:
                restore_attempted.append(True)
            if self == config_path and "mcpServers" in data and len(restore_attempted) == 0:
                # This is the normal write - make it fail
                raise IOError("Write failed")
            return original_write_text(self, data, encoding=encoding)
        
        monkeypatch.setattr(Path, "write_text", track_restore_write)
        monkeypatch.setattr("mind.cli.get_all_mcp_config_paths", lambda: [config_path])
        monkeypatch.setattr("mind.cli.get_mind_project_root", lambda: mock_project_root)
        
        success, status = ensure_mcp_configuration()
        
        # Should return False because write failed
        assert success is False
        assert "error" in status.lower() or "failed" in status.lower()
        
        # Key assertion: verify that invalid JSON was NOT explicitly restored
        # Since original_content is not set for invalid JSON, restore logic won't run
        assert len(restore_attempted) == 0, "Invalid JSON should not be restored"


