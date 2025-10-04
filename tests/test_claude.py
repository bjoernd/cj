"""Tests for Claude mode implementation."""

from unittest.mock import Mock, patch
from cjlib.claude import (
    ClaudeCommand,
    CONTAINER_CLAUDE_DIR,
    CONTAINER_WORKSPACE,
)
from cjlib.config import Config, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import ContainerManager
from cjlib.setup import SetupCommand


def test_get_volume_mounts():
    """Test volume mount construction."""
    config = Mock(spec=Config)
    config.get_claude_dir.return_value = "/test/path/.cj/claude"
    config.get_config_dir.return_value = "/test/path/.cj"

    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with patch("os.getcwd", return_value="/test/path"):
        mounts = claude_cmd._get_volume_mounts()

    # Verify correct volume mounts
    assert len(mounts) == 3
    assert f"/test/path:{CONTAINER_WORKSPACE}" in mounts
    assert f"/test/path/.cj:{CONTAINER_WORKSPACE}/.cj:ro" in mounts
    assert f"/test/path/.cj/claude:{CONTAINER_CLAUDE_DIR}" in mounts


def test_rebuild_image_success():
    """Test rebuilding image when it doesn't exist."""
    config = Mock(spec=Config)
    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)
    setup_cmd.run.return_value = 0

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    # Should not raise exception
    claude_cmd._rebuild_image()

    # Verify setup command was called
    setup_cmd.run.assert_called_once()


def test_rebuild_image_failure():
    """Test rebuild raises exception on failure."""
    config = Mock(spec=Config)
    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)
    setup_cmd.run.return_value = 1

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    try:
        claude_cmd._rebuild_image()
        assert False, "Should have raised Exception"
    except Exception as e:
        assert "Failed to rebuild container image" in str(e)


def test_run_success():
    """Test successful Claude launch."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_claude_dir.return_value = "/test/.cj/claude"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = True
    container_mgr.run_interactive.return_value = 0

    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with patch("os.getcwd", return_value="/test"):
        result = claude_cmd.run()

    # Verify success
    assert result == 0

    # Verify correct flow
    config.exists.assert_called_once()
    config.read_image_name.assert_called_once()
    container_mgr.image_exists.assert_called_once_with("cj-test-image")
    config.ensure_claude_dir.assert_called_once()
    container_mgr.run_interactive.assert_called_once()


def test_run_no_config():
    """Test error when .cj directory doesn't exist."""
    config = Mock(spec=Config)
    config.exists.return_value = False

    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    result = claude_cmd.run()

    # Verify failure
    assert result == 1

    # Verify container not launched
    container_mgr.run_interactive.assert_not_called()


def test_run_image_missing_rebuild_success():
    """Test rebuilding when image doesn't exist."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.side_effect = ["cj-test-image", "cj-test-image"]
    config.get_claude_dir.return_value = "/test/.cj/claude"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = False
    container_mgr.run_interactive.return_value = 0

    setup_cmd = Mock(spec=SetupCommand)
    setup_cmd.run.return_value = 0

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with patch("os.getcwd", return_value="/test"):
        result = claude_cmd.run()

    # Verify success after rebuild
    assert result == 0

    # Verify rebuild was called
    setup_cmd.run.assert_called_once()

    # Verify image name read twice (before and after rebuild)
    assert config.read_image_name.call_count == 2

    # Verify container launched
    container_mgr.run_interactive.assert_called_once()


def test_run_image_missing_rebuild_failure():
    """Test failure when image rebuild fails."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = False

    setup_cmd = Mock(spec=SetupCommand)
    setup_cmd.run.return_value = 1

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    result = claude_cmd.run()

    # Verify failure
    assert result == 1

    # Verify container not launched
    container_mgr.run_interactive.assert_not_called()


def test_run_config_not_found_error():
    """Test handling of ConfigNotFoundError."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.side_effect = ConfigNotFoundError("Config not found")

    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    result = claude_cmd.run()

    # Verify failure
    assert result == 1

    # Verify container not launched
    container_mgr.run_interactive.assert_not_called()


def test_run_image_name_not_found_error():
    """Test handling of ImageNameNotFoundError."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.side_effect = ImageNameNotFoundError("Image name not found")

    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    result = claude_cmd.run()

    # Verify failure
    assert result == 1

    # Verify container not launched
    container_mgr.run_interactive.assert_not_called()


def test_run_container_exit_code_propagated():
    """Test that container exit code is propagated."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_claude_dir.return_value = "/test/.cj/claude"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = True
    container_mgr.run_interactive.return_value = 42

    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with patch("os.getcwd", return_value="/test"):
        result = claude_cmd.run()

    # Verify exit code propagated
    assert result == 42


def test_run_interactive_called_with_correct_params():
    """Test run_interactive is called with correct parameters."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_claude_dir.return_value = "/test/.cj/claude"
    config.get_config_dir.return_value = "/test/.cj"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = True
    container_mgr.run_interactive.return_value = 0

    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with (
        patch("os.getcwd", return_value="/test"),
        patch.dict("os.environ", {"TERM": "xterm-256color"}),
    ):
        result = claude_cmd.run()

    # Verify run_interactive called with correct params
    assert result == 0
    container_mgr.run_interactive.assert_called_once_with(
        image="cj-test-image",
        working_dir=CONTAINER_WORKSPACE,
        volume_mounts=[
            f"/test:{CONTAINER_WORKSPACE}",
            f"/test/.cj:{CONTAINER_WORKSPACE}/.cj:ro",
            f"/test/.cj/claude:{CONTAINER_CLAUDE_DIR}",
        ],
        command=["claude"],
        env_vars=["TERM=xterm-256color"],
    )


def test_run_ensure_claude_dir_called():
    """Test that ensure_claude_dir is called before running container."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_claude_dir.return_value = "/test/.cj/claude"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = True
    container_mgr.run_interactive.return_value = 0

    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with patch("os.getcwd", return_value="/test"):
        result = claude_cmd.run()

    # Verify ensure_claude_dir was called
    assert result == 0
    config.ensure_claude_dir.assert_called_once()


def test_run_general_exception_handling():
    """Test handling of general exceptions."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.side_effect = Exception("Unexpected error")

    container_mgr = Mock(spec=ContainerManager)
    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    result = claude_cmd.run()

    # Verify failure
    assert result == 1

    # Verify container not launched
    container_mgr.run_interactive.assert_not_called()


def test_run_passes_term_from_environment():
    """Test that TERM environment variable is passed to container."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_claude_dir.return_value = "/test/.cj/claude"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = True
    container_mgr.run_interactive.return_value = 0

    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with (
        patch("os.getcwd", return_value="/test"),
        patch.dict("os.environ", {"TERM": "screen-256color"}),
    ):
        result = claude_cmd.run()

    # Verify TERM was passed from environment
    assert result == 0
    call_kwargs = container_mgr.run_interactive.call_args[1]
    assert "env_vars" in call_kwargs
    assert "TERM=screen-256color" in call_kwargs["env_vars"]


def test_run_defaults_term_when_not_set():
    """Test that TERM defaults to xterm-256color when not set in environment."""
    config = Mock(spec=Config)
    config.exists.return_value = True
    config.read_image_name.return_value = "cj-test-image"
    config.get_claude_dir.return_value = "/test/.cj/claude"

    container_mgr = Mock(spec=ContainerManager)
    container_mgr.image_exists.return_value = True
    container_mgr.run_interactive.return_value = 0

    setup_cmd = Mock(spec=SetupCommand)

    claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)

    with (
        patch("os.getcwd", return_value="/test"),
        patch.dict("os.environ", {}, clear=True),  # Clear TERM from environment
    ):
        result = claude_cmd.run()

    # Verify TERM defaults to xterm-256color
    assert result == 0
    call_kwargs = container_mgr.run_interactive.call_args[1]
    assert "env_vars" in call_kwargs
    assert "TERM=xterm-256color" in call_kwargs["env_vars"]
