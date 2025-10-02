"""Tests for CLI argument parsing and command routing."""

from unittest.mock import Mock, patch
from cjlib.cli import main
from cjlib.config import ConfigExistsError, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import ContainerNotAvailableError, ContainerBuildError, ContainerRunError


def test_setup_command_routing():
    """Test that setup subcommand routes to SetupCommand."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.return_value = 0
                    mock_setup_class.return_value = mock_setup

                    result = main()

                    assert result == 0
                    mock_setup_class.assert_called_once()
                    mock_setup.run.assert_called_once()


def test_update_command_routing():
    """Test that update subcommand routes to UpdateCommand."""
    with patch("sys.argv", ["cj", "update"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.UpdateCommand") as mock_update_class:
                    mock_update = Mock()
                    mock_update.run.return_value = 0
                    mock_update_class.return_value = mock_update

                    result = main()

                    assert result == 0
                    mock_update_class.assert_called_once()
                    mock_update.run.assert_called_once()


def test_default_command_routing():
    """Test that no subcommand routes to ClaudeCommand."""
    with patch("sys.argv", ["cj"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand"):
                    with patch("cjlib.cli.ClaudeCommand") as mock_claude_class:
                        mock_claude = Mock()
                        mock_claude.run.return_value = 0
                        mock_claude_class.return_value = mock_claude

                        result = main()

                        assert result == 0
                        mock_claude_class.assert_called_once()
                        mock_claude.run.assert_called_once()


def test_exit_code_propagation_setup():
    """Test that exit codes are propagated from SetupCommand."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.return_value = 42
                    mock_setup_class.return_value = mock_setup

                    result = main()

                    assert result == 42


def test_exit_code_propagation_update():
    """Test that exit codes are propagated from UpdateCommand."""
    with patch("sys.argv", ["cj", "update"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.UpdateCommand") as mock_update_class:
                    mock_update = Mock()
                    mock_update.run.return_value = 1
                    mock_update_class.return_value = mock_update

                    result = main()

                    assert result == 1


def test_exit_code_propagation_claude():
    """Test that exit codes are propagated from ClaudeCommand."""
    with patch("sys.argv", ["cj"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand"):
                    with patch("cjlib.cli.ClaudeCommand") as mock_claude_class:
                        mock_claude = Mock()
                        mock_claude.run.return_value = 5
                        mock_claude_class.return_value = mock_claude

                        result = main()

                        assert result == 5


def test_config_exists_error_handling():
    """Test handling of ConfigExistsError."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.side_effect = ConfigExistsError("Config exists")
                    mock_setup_class.return_value = mock_setup

                    result = main()

                    assert result == 1


def test_config_not_found_error_handling():
    """Test handling of ConfigNotFoundError."""
    with patch("sys.argv", ["cj", "update"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.UpdateCommand") as mock_update_class:
                    mock_update = Mock()
                    mock_update.run.side_effect = ConfigNotFoundError("Config not found")
                    mock_update_class.return_value = mock_update

                    result = main()

                    assert result == 1


def test_image_name_not_found_error_handling():
    """Test handling of ImageNameNotFoundError."""
    with patch("sys.argv", ["cj", "update"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.UpdateCommand") as mock_update_class:
                    mock_update = Mock()
                    mock_update.run.side_effect = ImageNameNotFoundError("Image name not found")
                    mock_update_class.return_value = mock_update

                    result = main()

                    assert result == 1


def test_container_not_available_error_handling():
    """Test handling of ContainerNotAvailableError."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.side_effect = ContainerNotAvailableError(
                        "Container not available"
                    )
                    mock_setup_class.return_value = mock_setup

                    result = main()

                    assert result == 1


def test_container_build_error_handling():
    """Test handling of ContainerBuildError."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.side_effect = ContainerBuildError("Build failed")
                    mock_setup_class.return_value = mock_setup

                    result = main()

                    assert result == 1


def test_container_run_error_handling():
    """Test handling of ContainerRunError."""
    with patch("sys.argv", ["cj"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand"):
                    with patch("cjlib.cli.ClaudeCommand") as mock_claude_class:
                        mock_claude = Mock()
                        mock_claude.run.side_effect = ContainerRunError("Run failed")
                        mock_claude_class.return_value = mock_claude

                        result = main()

                        assert result == 1


def test_general_exception_handling():
    """Test handling of general exceptions."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config"):
            with patch("cjlib.cli.ContainerManager"):
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.side_effect = Exception("Unexpected error")
                    mock_setup_class.return_value = mock_setup

                    result = main()

                    assert result == 1


def test_config_and_container_manager_instantiation():
    """Test that Config and ContainerManager are instantiated correctly."""
    with patch("sys.argv", ["cj", "setup"]):
        with patch("cjlib.cli.Config") as mock_config_class:
            with patch("cjlib.cli.ContainerManager") as mock_container_class:
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    mock_setup = Mock()
                    mock_setup.run.return_value = 0
                    mock_setup_class.return_value = mock_setup

                    main()

                    # Verify Config and ContainerManager were instantiated
                    mock_config_class.assert_called_once()
                    mock_container_class.assert_called_once()

                    # Verify they were passed to SetupCommand
                    config_instance = mock_config_class.return_value
                    container_instance = mock_container_class.return_value
                    mock_setup_class.assert_called_once_with(config_instance, container_instance)


def test_claude_mode_gets_setup_command():
    """Test that ClaudeCommand receives SetupCommand instance."""
    with patch("sys.argv", ["cj"]):
        with patch("cjlib.cli.Config") as mock_config_class:
            with patch("cjlib.cli.ContainerManager") as mock_container_class:
                with patch("cjlib.cli.SetupCommand") as mock_setup_class:
                    with patch("cjlib.cli.ClaudeCommand") as mock_claude_class:
                        mock_claude = Mock()
                        mock_claude.run.return_value = 0
                        mock_claude_class.return_value = mock_claude

                        main()

                        # Verify ClaudeCommand received Config, ContainerManager, and SetupCommand
                        config_instance = mock_config_class.return_value
                        container_instance = mock_container_class.return_value
                        setup_instance = mock_setup_class.return_value
                        mock_claude_class.assert_called_once_with(
                            config_instance, container_instance, setup_instance
                        )
