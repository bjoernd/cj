"""Tests for CLI argument parsing and command routing."""

import pytest
from unittest.mock import Mock, patch
from cjlib.cli import main
from cjlib.config import ConfigExistsError, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import ContainerNotAvailableError, ContainerBuildError, ContainerRunError


@pytest.fixture
def mock_config():
    """Fixture for mocked Config class."""
    with patch("cjlib.cli.Config") as mock:
        yield mock


@pytest.fixture
def mock_container_manager():
    """Fixture for mocked ContainerManager class."""
    with patch("cjlib.cli.ContainerManager") as mock:
        yield mock


@pytest.fixture
def mock_setup_command():
    """Fixture for mocked SetupCommand class."""
    with patch("cjlib.cli.SetupCommand") as mock:
        yield mock


@pytest.fixture
def mock_update_command():
    """Fixture for mocked UpdateCommand class."""
    with patch("cjlib.cli.UpdateCommand") as mock:
        yield mock


@pytest.fixture
def mock_claude_command():
    """Fixture for mocked ClaudeCommand class."""
    with patch("cjlib.cli.ClaudeCommand") as mock:
        yield mock


@pytest.fixture
def mock_shell_command():
    """Fixture for mocked ShellCommand class."""
    with patch("cjlib.cli.ShellCommand") as mock:
        yield mock


@pytest.mark.parametrize(
    "argv,command_fixture",
    [
        (["cj", "setup"], "mock_setup_command"),
        (["cj", "update"], "mock_update_command"),
        (["cj", "shell"], "mock_shell_command"),
    ],
)
def test_command_routing(argv, command_fixture, request, mock_config, mock_container_manager):
    """Test that setup, update, and shell subcommands route to correct handlers."""
    mock_cmd_class = request.getfixturevalue(command_fixture)
    mock_cmd = Mock()
    mock_cmd.run.return_value = 0
    mock_cmd_class.return_value = mock_cmd

    with patch("sys.argv", argv):
        result = main()

    assert result == 0
    mock_cmd_class.assert_called_once()
    mock_cmd.run.assert_called_once()


def test_default_command_routing(
    mock_config, mock_container_manager, mock_setup_command, mock_claude_command
):
    """Test that no subcommand routes to ClaudeCommand."""
    mock_claude = Mock()
    mock_claude.run.return_value = 0
    mock_claude_command.return_value = mock_claude

    with patch("sys.argv", ["cj"]):
        result = main()

    assert result == 0
    mock_claude_command.assert_called_once()
    mock_claude.run.assert_called_once()


@pytest.mark.parametrize(
    "argv,command_fixture,exit_code",
    [
        (["cj", "setup"], "mock_setup_command", 42),
        (["cj", "update"], "mock_update_command", 1),
        (["cj", "shell"], "mock_shell_command", 3),
    ],
)
def test_exit_code_propagation(
    argv, command_fixture, exit_code, request, mock_config, mock_container_manager
):
    """Test that exit codes are propagated from commands."""
    mock_cmd_class = request.getfixturevalue(command_fixture)
    mock_cmd = Mock()
    mock_cmd.run.return_value = exit_code
    mock_cmd_class.return_value = mock_cmd

    with patch("sys.argv", argv):
        result = main()

    assert result == exit_code


def test_exit_code_propagation_claude(
    mock_config, mock_container_manager, mock_setup_command, mock_claude_command
):
    """Test that exit codes are propagated from ClaudeCommand."""
    mock_claude = Mock()
    mock_claude.run.return_value = 5
    mock_claude_command.return_value = mock_claude

    with patch("sys.argv", ["cj"]):
        result = main()

    assert result == 5


@pytest.mark.parametrize(
    "argv,command_fixture,exception",
    [
        (["cj", "setup"], "mock_setup_command", ConfigExistsError("Config exists")),
        (["cj", "update"], "mock_update_command", ConfigNotFoundError("Config not found")),
        (
            ["cj", "update"],
            "mock_update_command",
            ImageNameNotFoundError("Image name not found"),
        ),
        (
            ["cj", "setup"],
            "mock_setup_command",
            ContainerNotAvailableError("Container not available"),
        ),
        (["cj", "setup"], "mock_setup_command", ContainerBuildError("Build failed")),
        (["cj", "setup"], "mock_setup_command", Exception("Unexpected error")),
        (["cj", "shell"], "mock_shell_command", ConfigNotFoundError("Config not found")),
    ],
)
def test_error_handling(
    argv, command_fixture, exception, request, mock_config, mock_container_manager
):
    """Test handling of various exceptions."""
    mock_cmd_class = request.getfixturevalue(command_fixture)
    mock_cmd = Mock()
    mock_cmd.run.side_effect = exception
    mock_cmd_class.return_value = mock_cmd

    with patch("sys.argv", argv):
        result = main()

    assert result == 1


def test_container_run_error_handling(
    mock_config, mock_container_manager, mock_setup_command, mock_claude_command
):
    """Test handling of ContainerRunError."""
    mock_claude = Mock()
    mock_claude.run.side_effect = ContainerRunError("Run failed")
    mock_claude_command.return_value = mock_claude

    with patch("sys.argv", ["cj"]):
        result = main()

    assert result == 1


def test_config_and_container_manager_instantiation(mock_setup_command):
    """Test that Config and ContainerManager are instantiated correctly."""
    with patch("cjlib.cli.Config") as mock_config_class:
        with patch("cjlib.cli.ContainerManager") as mock_container_class:
            mock_setup = Mock()
            mock_setup.run.return_value = 0
            mock_setup_command.return_value = mock_setup

            with patch("sys.argv", ["cj", "setup"]):
                main()

            # Verify Config and ContainerManager were instantiated
            mock_config_class.assert_called_once()
            mock_container_class.assert_called_once()

            # Verify they were passed to SetupCommand
            config_instance = mock_config_class.return_value
            container_instance = mock_container_class.return_value
            mock_setup_command.assert_called_once_with(config_instance, container_instance)


def test_claude_mode_gets_setup_command(mock_setup_command, mock_claude_command):
    """Test that ClaudeCommand receives SetupCommand instance."""
    with patch("cjlib.cli.Config") as mock_config_class:
        with patch("cjlib.cli.ContainerManager") as mock_container_class:
            mock_claude = Mock()
            mock_claude.run.return_value = 0
            mock_claude_command.return_value = mock_claude

            with patch("sys.argv", ["cj"]):
                main()

            # Verify ClaudeCommand received Config, ContainerManager, and SetupCommand
            config_instance = mock_config_class.return_value
            container_instance = mock_container_class.return_value
            setup_instance = mock_setup_command.return_value
            mock_claude_command.assert_called_once_with(
                config_instance, container_instance, setup_instance
            )
