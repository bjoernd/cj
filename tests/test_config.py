"""Tests for cjlib.config module."""

import pytest
from pathlib import Path
from cjlib.config import (
    Config,
    ConfigExistsError,
    ImageNameNotFoundError,
    CONFIG_DIR,
    IMAGE_NAME_FILE,
    DOCKERFILE_NAME,
    CLAUDE_DIR,
    VENV_DIR,
    SSH_DIR,
    SSH_PRIVATE_KEY,
    SSH_PUBLIC_KEY,
)


class TestConfig:
    """Tests for Config class."""

    def test_init_with_default_directory(self):
        """Test Config initialization with default directory."""
        config = Config()
        assert config.base_dir == Path(".").resolve()

    def test_init_with_custom_directory(self, tmp_path):
        """Test Config initialization with custom directory."""
        config = Config(str(tmp_path))
        assert config.base_dir == tmp_path

    def test_get_config_dir(self, tmp_path):
        """Test get_config_dir returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR)
        assert config.get_config_dir() == expected

    def test_exists_returns_false_when_no_config(self, tmp_path):
        """Test exists() returns False when .cj doesn't exist."""
        config = Config(str(tmp_path))
        assert config.exists() is False

    def test_exists_returns_true_when_config_exists(self, tmp_path):
        """Test exists() returns True when .cj exists."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()
        assert config.exists() is True

    def test_create_config_dir_successfully_creates_directory(self, tmp_path):
        """Test create_config_dir() creates directory successfully."""
        config = Config(str(tmp_path))
        config.create_config_dir()
        assert (tmp_path / CONFIG_DIR).is_dir()

    def test_create_config_dir_raises_error_when_exists(self, tmp_path):
        """Test create_config_dir() raises ConfigExistsError when already exists."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()
        with pytest.raises(ConfigExistsError) as exc_info:
            config.create_config_dir()
        assert "already exists" in str(exc_info.value)

    def test_get_image_name_path(self, tmp_path):
        """Test get_image_name_path() returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / IMAGE_NAME_FILE)
        assert config.get_image_name_path() == expected

    def test_write_and_read_image_name(self, tmp_path):
        """Test write_image_name() and read_image_name() work together."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()

        test_name = "cj-happy-turtle"
        config.write_image_name(test_name)

        assert config.read_image_name() == test_name

    def test_read_image_name_raises_error_when_not_found(self, tmp_path):
        """Test read_image_name() raises ImageNameNotFoundError when file doesn't exist."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()

        with pytest.raises(ImageNameNotFoundError) as exc_info:
            config.read_image_name()
        assert "not found" in str(exc_info.value)

    def test_get_dockerfile_path(self, tmp_path):
        """Test get_dockerfile_path() returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / DOCKERFILE_NAME)
        assert config.get_dockerfile_path() == expected

    def test_get_claude_dir(self, tmp_path):
        """Test get_claude_dir() returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / CLAUDE_DIR)
        assert config.get_claude_dir() == expected

    def test_ensure_claude_dir_creates_directory(self, tmp_path):
        """Test ensure_claude_dir() creates directory if it doesn't exist."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()

        config.ensure_claude_dir()

        assert (tmp_path / CONFIG_DIR / CLAUDE_DIR).is_dir()

    def test_ensure_claude_dir_is_idempotent(self, tmp_path):
        """Test ensure_claude_dir() doesn't error if directory already exists."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()
        (tmp_path / CONFIG_DIR / CLAUDE_DIR).mkdir()

        # Should not raise error
        config.ensure_claude_dir()

        assert (tmp_path / CONFIG_DIR / CLAUDE_DIR).is_dir()

    def test_get_venv_dir(self, tmp_path):
        """Test get_venv_dir() returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / VENV_DIR)
        assert config.get_venv_dir() == expected

    def test_cleanup_removes_entire_config_directory(self, tmp_path):
        """Test cleanup() removes entire .cj directory and contents."""
        config = Config(str(tmp_path))

        # Create config directory with various subdirectories and files
        (tmp_path / CONFIG_DIR).mkdir()
        (tmp_path / CONFIG_DIR / CLAUDE_DIR).mkdir()
        (tmp_path / CONFIG_DIR / VENV_DIR).mkdir()
        (tmp_path / CONFIG_DIR / IMAGE_NAME_FILE).write_text("test-image")
        (tmp_path / CONFIG_DIR / DOCKERFILE_NAME).write_text("FROM ubuntu")

        config.cleanup()

        assert not (tmp_path / CONFIG_DIR).exists()

    def test_cleanup_when_config_doesnt_exist(self, tmp_path):
        """Test cleanup() doesn't error when .cj doesn't exist."""
        config = Config(str(tmp_path))

        # Should not raise error
        config.cleanup()

        assert not (tmp_path / CONFIG_DIR).exists()

    def test_write_image_name_strips_whitespace(self, tmp_path):
        """Test that image name is stored exactly as written."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()

        test_name = "cj-test-name"
        config.write_image_name(test_name)

        # Read should strip whitespace
        assert config.read_image_name() == test_name

    def test_read_image_name_strips_whitespace(self, tmp_path):
        """Test that read_image_name() strips whitespace."""
        config = Config(str(tmp_path))
        (tmp_path / CONFIG_DIR).mkdir()

        # Write with extra whitespace
        (tmp_path / CONFIG_DIR / IMAGE_NAME_FILE).write_text("  cj-test-name\n  ")

        assert config.read_image_name() == "cj-test-name"

    def test_get_ssh_dir(self, tmp_path):
        """Test get_ssh_dir returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / SSH_DIR)
        assert config.get_ssh_dir() == expected

    def test_ensure_ssh_dir_creates_directory(self, tmp_path):
        """Test ensure_ssh_dir creates directory."""
        config = Config(str(tmp_path))
        ssh_path = tmp_path / CONFIG_DIR / SSH_DIR

        config.ensure_ssh_dir()

        assert ssh_path.exists()
        assert ssh_path.is_dir()

    def test_ensure_ssh_dir_is_idempotent(self, tmp_path):
        """Test ensure_ssh_dir can be called multiple times."""
        config = Config(str(tmp_path))
        ssh_path = tmp_path / CONFIG_DIR / SSH_DIR

        config.ensure_ssh_dir()
        config.ensure_ssh_dir()

        assert ssh_path.exists()

    def test_get_ssh_private_key_path(self, tmp_path):
        """Test get_ssh_private_key_path returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / SSH_DIR / SSH_PRIVATE_KEY)
        assert config.get_ssh_private_key_path() == expected

    def test_get_ssh_public_key_path(self, tmp_path):
        """Test get_ssh_public_key_path returns correct path."""
        config = Config(str(tmp_path))
        expected = str(tmp_path / CONFIG_DIR / SSH_DIR / SSH_PUBLIC_KEY)
        assert config.get_ssh_public_key_path() == expected
