"""Tests for update mode implementation."""

from unittest.mock import Mock
from cjlib.update import UpdateCommand
from cjlib.config import Config, ConfigNotFoundError, DOCKERFILE_TEMPLATE
from cjlib.container import ContainerManager


def test_regenerate_dockerfile(tmp_path):
    """Test Dockerfile regeneration."""
    config = Config(str(tmp_path))
    config_dir = tmp_path / ".cj"
    config_dir.mkdir()

    config.generate_and_write_dockerfile()

    dockerfile_path = config_dir / "Dockerfile"
    # Verify file was created with correct content
    assert dockerfile_path.exists()
    content = dockerfile_path.read_text()
    assert content == DOCKERFILE_TEMPLATE


def test_run_success(tmp_path):
    """Test successful update flow."""
    config_dir = tmp_path / ".cj"
    config_dir.mkdir(parents=True, exist_ok=True)

    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = str(config_dir / "Dockerfile")
    config.read_extra_packages.return_value = []
    config.generate_and_write_dockerfile.return_value = None

    container_mgr = Mock(spec=ContainerManager)

    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify success
    assert result == 0

    # Verify correct flow
    config.exists.assert_called_once()
    config.read_image_name.assert_called_once()
    config.read_extra_packages.assert_called_once()
    config.generate_and_write_dockerfile.assert_called_once()
    config.get_dockerfile_path.assert_called_once()
    container_mgr.build_image.assert_called_once()


def test_run_no_config():
    """Test failure when .cj directory doesn't exist."""
    config = Mock(spec=Config)
    config.exists.return_value = False

    container_mgr = Mock(spec=ContainerManager)
    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify failure
    assert result == 1

    # Verify no operations performed
    config.read_image_name.assert_not_called()
    container_mgr.build_image.assert_not_called()


def test_run_image_name_not_found():
    """Test failure when image name file doesn't exist."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.side_effect = ConfigNotFoundError("Image name not found")

    container_mgr = Mock(spec=ContainerManager)
    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify failure
    assert result == 1

    # Verify build not called
    container_mgr.build_image.assert_not_called()


def test_run_build_failure(tmp_path):
    """Test failure when image build fails."""
    config_dir = tmp_path / ".cj"
    config_dir.mkdir(parents=True, exist_ok=True)

    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = str(config_dir / "Dockerfile")
    config.read_extra_packages.return_value = []
    config.generate_and_write_dockerfile.return_value = None

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.build_image.side_effect = Exception("Build failed")

    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify failure
    assert result == 1


def test_run_same_image_name_reused(tmp_path):
    """Test that the same image name is reused during update."""
    config_dir = tmp_path / ".cj"
    config_dir.mkdir(parents=True, exist_ok=True)

    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-happy-turtle"
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = str(config_dir / "Dockerfile")
    config.read_extra_packages.return_value = []
    config.generate_and_write_dockerfile.return_value = None

    container_mgr = Mock(spec=ContainerManager)

    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify same image name used for rebuild
    assert result == 0
    container_mgr.build_image.assert_called_once()
    call_args = container_mgr.build_image.call_args
    assert call_args[0][1] == "cj-happy-turtle"  # Second arg is tag


def test_run_dockerfile_regenerated(tmp_path):
    """Test that Dockerfile is regenerated during update."""
    config_dir = tmp_path / ".cj"
    config_dir.mkdir(parents=True, exist_ok=True)
    dockerfile_path = config_dir / "Dockerfile"

    # Create existing Dockerfile with custom content
    dockerfile_path.write_text("# Custom Dockerfile\nFROM custom:image\n")

    # Use real Config for this test to actually write the file
    config = Config(str(tmp_path))

    # Write image name file (required for update to work)
    config.write_image_name("cj-test-image")

    container_mgr = Mock(spec=ContainerManager)

    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify Dockerfile was regenerated (user customizations lost)
    assert result == 0
    content = dockerfile_path.read_text()
    assert content == DOCKERFILE_TEMPLATE
    assert "# Custom Dockerfile" not in content


def test_run_build_image_called_with_correct_params(tmp_path):
    """Test build_image is called with correct parameters."""
    config_dir = tmp_path / ".cj"
    config_dir.mkdir(parents=True, exist_ok=True)
    dockerfile_path = str(config_dir / "Dockerfile")

    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_config_dir.return_value = str(config_dir)
    config.get_dockerfile_path.return_value = dockerfile_path
    config.read_extra_packages.return_value = []
    config.generate_and_write_dockerfile.return_value = None

    container_mgr = Mock(spec=ContainerManager)

    update_cmd = UpdateCommand(config, container_mgr)

    result = update_cmd.run()

    # Verify build_image called with correct params
    assert result == 0
    expected_log_file = str(config_dir / "update.log")
    container_mgr.build_image.assert_called_once_with(
        dockerfile_path, "cj-test-image", str(tmp_path), expected_log_file
    )
