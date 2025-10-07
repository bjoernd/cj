"""Shared fixtures for test suite."""

import pytest
from unittest.mock import Mock
from cjlib.config import Config
from cjlib.container import ContainerManager
from cjlib.setup import SetupCommand


@pytest.fixture
def mock_config(tmp_path):
    """Fixture providing a mocked Config instance with common setup."""
    config = Mock(spec=Config)
    config_dir = tmp_path / ".cj"
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = str(config_dir / "Dockerfile")
    config.get_claude_dir.return_value = str(config_dir / "claude")
    config.get_venv_dir.return_value = str(config_dir / "venv")
    config.get_image_name_path.return_value = str(config_dir / "image_name")
    return config


@pytest.fixture
def mock_container_manager():
    """Fixture providing a mocked ContainerManager instance."""
    return Mock(spec=ContainerManager)


@pytest.fixture
def mock_setup_command():
    """Fixture providing a mocked SetupCommand instance."""
    return Mock(spec=SetupCommand)
