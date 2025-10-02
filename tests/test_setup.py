"""Tests for setup mode implementation."""

from unittest.mock import Mock, patch
from cjlib.setup import SetupCommand, DOCKERFILE_TEMPLATE
from cjlib.config import Config
from cjlib.container import ContainerManager


def test_generate_dockerfile(tmp_path):
    """Test Dockerfile generation."""
    config = Mock(spec=Config)
    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = SetupCommand(config, container_mgr)

    dockerfile_path = tmp_path / "Dockerfile"
    setup_cmd._generate_dockerfile(str(dockerfile_path))

    # Verify file was created with correct content
    assert dockerfile_path.exists()
    content = dockerfile_path.read_text()
    assert content == DOCKERFILE_TEMPLATE


def test_dockerfile_template_content():
    """Test that Dockerfile template includes all required tools."""
    assert "FROM ubuntu:25.04" in DOCKERFILE_TEMPLATE
    assert "gcc g++" in DOCKERFILE_TEMPLATE
    assert "clang" in DOCKERFILE_TEMPLATE
    assert "python3" in DOCKERFILE_TEMPLATE
    assert "vim neovim" in DOCKERFILE_TEMPLATE
    assert "zsh" in DOCKERFILE_TEMPLATE
    assert "rustup" in DOCKERFILE_TEMPLATE
    assert "nodejs" in DOCKERFILE_TEMPLATE
    assert "oh-my-zsh" in DOCKERFILE_TEMPLATE
    assert "@anthropic-ai/claude-code" in DOCKERFILE_TEMPLATE
    assert "WORKDIR /workspace" in DOCKERFILE_TEMPLATE


def test_cleanup_on_failure():
    """Test cleanup removes .cj directory on failure."""
    config = Mock(spec=Config)
    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = SetupCommand(config, container_mgr)

    setup_cmd._cleanup_on_failure()

    config.cleanup.assert_called_once()


def test_cleanup_on_failure_ignores_errors():
    """Test cleanup ignores errors during cleanup."""
    config = Mock(spec=Config)
    config.cleanup.side_effect = Exception("Cleanup failed")
    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = SetupCommand(config, container_mgr)

    # Should not raise exception
    setup_cmd._cleanup_on_failure()


def test_run_success(tmp_path):
    """Test successful setup flow."""
    config_dir = tmp_path / ".cj"

    config = Mock(spec=Config)
    config.exists.return_value = False
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = str(config_dir / "Dockerfile")

    # Mock create_config_dir to actually create the directory
    def create_dir():
        config_dir.mkdir(parents=True, exist_ok=True)

    config.create_config_dir.side_effect = create_dir

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-test-image"):
        result = setup_cmd.run()

    # Verify success
    assert result == 0

    # Verify correct flow
    config.exists.assert_called_once()
    container_mgr.check_container_available.assert_called_once()
    config.create_config_dir.assert_called_once()
    config.get_dockerfile_path.assert_called_once()
    container_mgr.build_image.assert_called_once()
    config.write_image_name.assert_called_once_with("cj-test-image")


def test_run_config_already_exists():
    """Test failure when .cj directory already exists."""
    config = Mock(spec=Config)
    config.exists.return_value = True

    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = SetupCommand(config, container_mgr)

    result = setup_cmd.run()

    # Verify failure
    assert result == 1

    # Verify container operations not called
    container_mgr.check_container_available.assert_not_called()
    config.create_config_dir.assert_not_called()


def test_run_container_not_available():
    """Test failure when container command not available."""
    config = Mock(spec=Config)
    config.exists.return_value = False

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = False

    setup_cmd = SetupCommand(config, container_mgr)

    result = setup_cmd.run()

    # Verify failure
    assert result == 1

    # Verify config not created
    config.create_config_dir.assert_not_called()


def test_run_build_failure_cleanup(tmp_path):
    """Test cleanup on build failure."""
    config = Mock(spec=Config)
    config.exists.return_value = False
    config.get_config_dir.return_value = str(tmp_path / ".cj")
    config.get_dockerfile_path.return_value = str(tmp_path / ".cj" / "Dockerfile")

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True
    container_mgr.build_image.side_effect = Exception("Build failed")

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-test-image"):
        result = setup_cmd.run()

    # Verify failure
    assert result == 1

    # Verify cleanup was called
    config.cleanup.assert_called_once()

    # Verify image name not written
    config.write_image_name.assert_not_called()


def test_run_image_name_written_with_correct_value(tmp_path):
    """Test image name is written correctly."""
    config_dir = tmp_path / ".cj"

    config = Mock(spec=Config)
    config.exists.return_value = False
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = str(config_dir / "Dockerfile")

    # Mock create_config_dir to actually create the directory
    def create_dir():
        config_dir.mkdir(parents=True, exist_ok=True)

    config.create_config_dir.side_effect = create_dir

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-happy-turtle"):
        result = setup_cmd.run()

    # Verify image name written correctly
    assert result == 0
    config.write_image_name.assert_called_once_with("cj-happy-turtle")


def test_run_build_image_called_with_correct_params(tmp_path):
    """Test build_image is called with correct parameters."""
    config_dir = tmp_path / ".cj"
    dockerfile_path = str(config_dir / "Dockerfile")

    config = Mock(spec=Config)
    config.exists.return_value = False
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = dockerfile_path

    # Mock create_config_dir to actually create the directory
    def create_dir():
        config_dir.mkdir(parents=True, exist_ok=True)

    config.create_config_dir.side_effect = create_dir

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-test-image"):
        result = setup_cmd.run()

    # Verify build_image called with correct params
    assert result == 0
    container_mgr.build_image.assert_called_once_with(
        dockerfile_path, "cj-test-image", str(tmp_path)
    )


def test_run_dockerfile_written_before_build(tmp_path):
    """Test that Dockerfile is written before image build."""
    dockerfile_path = tmp_path / ".cj" / "Dockerfile"
    dockerfile_path.parent.mkdir(parents=True)

    config = Mock(spec=Config)
    config.exists.return_value = False
    config.get_config_dir.return_value = str(tmp_path / ".cj")
    config.get_dockerfile_path.return_value = str(dockerfile_path)

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.check_container_available.return_value = True

    # Track if Dockerfile exists when build_image is called
    dockerfile_exists_during_build = False

    def check_dockerfile(*args, **kwargs):
        nonlocal dockerfile_exists_during_build
        dockerfile_exists_during_build = dockerfile_path.exists()

    container_mgr.build_image.side_effect = check_dockerfile

    setup_cmd = SetupCommand(config, container_mgr)

    with patch("cjlib.setup.generate_name", return_value="cj-test-image"):
        result = setup_cmd.run()

    # Verify Dockerfile exists when build is called
    assert result == 0
    assert dockerfile_exists_during_build
