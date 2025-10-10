"""Tests for extra packages functionality."""

from unittest.mock import Mock, patch
from cjlib.config import Config, DOCKERFILE_TEMPLATE
from cjlib.setup import SetupCommand
from cjlib.update import UpdateCommand
from cjlib.container import ContainerManager


def test_write_and_read_extra_packages(tmp_path):
    """Test writing and reading extra packages list."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    packages = ["htop", "tmux", "wget"]
    config.write_extra_packages(packages)

    # Read back and verify
    read_packages = config.read_extra_packages()
    assert read_packages == packages


def test_read_extra_packages_empty_file(tmp_path):
    """Test reading from empty extra-packages file."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    # Create empty file
    (config_dir / "extra-packages").write_text("")

    packages = config.read_extra_packages()
    assert packages == []


def test_read_extra_packages_nonexistent_file(tmp_path):
    """Test reading when extra-packages file doesn't exist."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    packages = config.read_extra_packages()
    assert packages == []


def test_extract_packages_from_dockerfile():
    """Test extracting packages from Dockerfile."""
    config = Config(".")

    packages = config._extract_packages_from_dockerfile(DOCKERFILE_TEMPLATE)

    # Verify known packages are extracted
    assert "gcc" in packages
    assert "g++" in packages
    assert "clang" in packages
    assert "python3" in packages
    assert "vim" in packages
    assert "neovim" in packages
    assert "zsh" in packages
    assert "curl" in packages
    assert "git" in packages


def test_generate_dockerfile_with_new_packages(tmp_path):
    """Test generating Dockerfile with new packages."""
    config = Config(str(tmp_path))

    # Generate with new packages
    content = config._generate_dockerfile_with_packages(["htop", "tmux", "wget"])

    # Verify new packages are added
    assert "htop" in content
    assert "tmux" in content
    assert "wget" in content

    # Verify base template is still there
    assert "FROM ubuntu:25.04" in content
    assert "claude-code" in content


def test_generate_dockerfile_with_duplicate_packages(tmp_path):
    """Test that duplicate packages are filtered out."""
    config = Config(str(tmp_path))

    # Try to add packages that already exist in template
    content = config._generate_dockerfile_with_packages(["gcc", "git", "curl"])

    # Should return unchanged template since all packages already exist
    assert content == DOCKERFILE_TEMPLATE


def test_generate_dockerfile_with_mixed_packages(tmp_path):
    """Test with both new and existing packages."""
    config = Config(str(tmp_path))

    # Mix of existing and new packages
    content = config._generate_dockerfile_with_packages(["gcc", "htop", "python3", "tmux"])

    # New packages should be added
    assert "htop" in content
    assert "tmux" in content

    # Verify gcc and python3 are in the apt-get install line (they're already there)
    assert "gcc" in content
    assert "python3" in content


def test_generate_and_write_dockerfile_without_extra_packages(tmp_path):
    """Test generating Dockerfile without extra packages."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    config.generate_and_write_dockerfile()

    dockerfile_path = config_dir / "Dockerfile"
    assert dockerfile_path.exists()

    content = dockerfile_path.read_text()
    assert content == DOCKERFILE_TEMPLATE


def test_generate_and_write_dockerfile_with_extra_packages(tmp_path):
    """Test generating Dockerfile with extra packages."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    config.generate_and_write_dockerfile(["htop", "tmux"])

    dockerfile_path = config_dir / "Dockerfile"
    assert dockerfile_path.exists()

    content = dockerfile_path.read_text()
    assert "htop" in content
    assert "tmux" in content


def test_setup_with_extra_packages(tmp_path):
    """Test setup command with extra packages."""
    config = Config(str(tmp_path))
    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-test-image"):
        result = setup_cmd.run(extra_packages=["htop", "tmux", "wget"])

    # Verify success
    assert result == 0

    # Verify packages were stored
    stored_packages = config.read_extra_packages()
    assert set(stored_packages) == {"htop", "tmux", "wget"}

    # Verify Dockerfile contains the packages
    dockerfile_path = tmp_path / ".cj" / "Dockerfile"
    content = dockerfile_path.read_text()
    assert "htop" in content
    assert "tmux" in content
    assert "wget" in content


def test_setup_without_extra_packages(tmp_path):
    """Test setup command without extra packages."""
    config = Config(str(tmp_path))
    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-test-image"):
        result = setup_cmd.run(extra_packages=None)

    # Verify success
    assert result == 0

    # Verify no extra packages stored
    stored_packages = config.read_extra_packages()
    assert stored_packages == []


def test_update_with_new_extra_packages(tmp_path):
    """Test update command adding new extra packages."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    # Setup initial state with some packages
    config.write_image_name("cj-test-image")
    config.write_extra_packages(["htop", "tmux"])

    container_mgr = Mock(spec=ContainerManager)
    update_cmd = UpdateCommand(config, container_mgr)

    # Run update with additional packages
    result = update_cmd.run(extra_packages=["wget", "ncdu"])

    # Verify success
    assert result == 0

    # Verify packages were merged
    stored_packages = config.read_extra_packages()
    assert set(stored_packages) == {"htop", "tmux", "wget", "ncdu"}

    # Verify Dockerfile contains all packages
    dockerfile_path = config_dir / "Dockerfile"
    content = dockerfile_path.read_text()
    assert "htop" in content
    assert "tmux" in content
    assert "wget" in content
    assert "ncdu" in content


def test_update_with_duplicate_extra_packages(tmp_path):
    """Test update command with duplicate packages."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    # Setup initial state
    config.write_image_name("cj-test-image")
    config.write_extra_packages(["htop", "tmux"])

    container_mgr = Mock(spec=ContainerManager)
    update_cmd = UpdateCommand(config, container_mgr)

    # Run update with some duplicate packages
    result = update_cmd.run(extra_packages=["tmux", "wget", "htop"])

    # Verify success
    assert result == 0

    # Verify packages were merged (no duplicates in stored list)
    stored_packages = config.read_extra_packages()
    assert set(stored_packages) == {"htop", "tmux", "wget"}

    # Verify all packages are present in Dockerfile
    dockerfile_path = config_dir / "Dockerfile"
    content = dockerfile_path.read_text()
    assert "htop" in content
    assert "tmux" in content
    assert "wget" in content


def test_update_without_new_extra_packages_preserves_existing(tmp_path):
    """Test update command without new packages preserves existing ones."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    # Setup initial state with packages
    config.write_image_name("cj-test-image")
    config.write_extra_packages(["htop", "tmux"])

    container_mgr = Mock(spec=ContainerManager)
    update_cmd = UpdateCommand(config, container_mgr)

    # Run update without new packages
    result = update_cmd.run(extra_packages=None)

    # Verify success
    assert result == 0

    # Verify existing packages are preserved
    stored_packages = config.read_extra_packages()
    assert set(stored_packages) == {"htop", "tmux"}

    # Verify Dockerfile contains existing packages
    dockerfile_path = config_dir / "Dockerfile"
    content = dockerfile_path.read_text()
    assert "htop" in content
    assert "tmux" in content


def test_cli_setup_with_extra_packages_parsing():
    """Test CLI parsing of --extra-packages for setup command."""
    from cjlib.cli import main

    with patch("cjlib.cli.SetupCommand") as mock_setup:
        with patch("sys.argv", ["cj", "setup", "--extra-packages", "htop tmux wget"]):
            mock_cmd = Mock()
            mock_cmd.run.return_value = 0
            mock_setup.return_value = mock_cmd

            result = main()

            # Verify setup was called with parsed packages
            assert result == 0
            mock_cmd.run.assert_called_once_with(["htop", "tmux", "wget"])


def test_cli_update_with_extra_packages_parsing():
    """Test CLI parsing of --extra-packages for update command."""
    from cjlib.cli import main

    with patch("cjlib.cli.UpdateCommand") as mock_update:
        with patch("sys.argv", ["cj", "update", "--extra-packages", "ncdu tree"]):
            mock_cmd = Mock()
            mock_cmd.run.return_value = 0
            mock_update.return_value = mock_cmd

            result = main()

            # Verify update was called with parsed packages
            assert result == 0
            mock_cmd.run.assert_called_once_with(["ncdu", "tree"])
