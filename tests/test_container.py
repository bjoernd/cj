"""Tests for the container module."""

import subprocess
from unittest.mock import Mock, patch
import pytest
from cjlib.container import (
    ContainerManager,
    ContainerBuildError,
    ContainerRunError,
    SSHKeyError,
    _run_command,
    setup_ssh_keys,
)


class TestRunCommand:
    """Tests for _run_command helper function."""

    @patch("subprocess.run")
    def test_run_command_with_defaults(self, mock_run):
        """Test _run_command with default parameters."""
        mock_result = Mock(returncode=0, stdout="output", stderr="")
        mock_run.return_value = mock_result

        result = _run_command(["echo", "hello"])

        mock_run.assert_called_once_with(
            ["echo", "hello"], check=True, capture_output=True, text=True
        )
        assert result == mock_result

    @patch("subprocess.run")
    def test_run_command_without_check(self, mock_run):
        """Test _run_command with check=False."""
        mock_result = Mock(returncode=1)
        mock_run.return_value = mock_result

        result = _run_command(["false"], check=False)

        mock_run.assert_called_once_with(["false"], check=False, capture_output=True, text=True)
        assert result == mock_result

    @patch("subprocess.run")
    def test_run_command_without_capture(self, mock_run):
        """Test _run_command with capture_output=False."""
        mock_result = Mock(returncode=0)
        mock_run.return_value = mock_result

        result = _run_command(["echo", "hello"], capture_output=False)

        mock_run.assert_called_once_with(
            ["echo", "hello"], check=True, capture_output=False, text=True
        )
        assert result == mock_result


class TestContainerManager:
    """Tests for ContainerManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ContainerManager()

    @patch("shutil.which")
    def test_check_container_available_returns_true(self, mock_which):
        """Test that check_container_available returns True when command exists."""
        mock_which.return_value = "/usr/bin/container"

        result = self.manager.check_container_available()

        assert result is True
        mock_which.assert_called_once_with("container")

    @patch("shutil.which")
    def test_check_container_available_returns_false(self, mock_which):
        """Test that check_container_available returns False when command not found."""
        mock_which.return_value = None

        result = self.manager.check_container_available()

        assert result is False
        mock_which.assert_called_once_with("container")

    @patch("cjlib.container._run_command")
    def test_build_image_success(self, mock_run):
        """Test successful image build."""
        mock_run.return_value = Mock(returncode=0)

        self.manager.build_image("/path/to/Dockerfile", "my-image:latest", "/build/context")

        mock_run.assert_called_once_with(
            [
                "container",
                "build",
                "-t",
                "my-image:latest",
                "-f",
                "/path/to/Dockerfile",
                "/build/context",
            ]
        )

    @patch("cjlib.container._run_command")
    def test_build_image_raises_on_failure(self, mock_run):
        """Test that build_image raises ContainerBuildError on failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "container build")

        with pytest.raises(ContainerBuildError, match="Failed to build image"):
            self.manager.build_image("/path/to/Dockerfile", "my-image", "/context")

    @patch("cjlib.container._run_command")
    def test_image_exists_returns_true(self, mock_run):
        """Test that image_exists returns True when image is found."""
        mock_run.return_value = Mock(returncode=0, stdout="my-image:latest\nother-image:v1\n")

        result = self.manager.image_exists("my-image:latest")

        assert result is True
        mock_run.assert_called_once_with(["container", "image", "list"], check=False)

    @patch("cjlib.container._run_command")
    def test_image_exists_returns_false(self, mock_run):
        """Test that image_exists returns False when image not found."""
        mock_run.return_value = Mock(returncode=0, stdout="other-image:v1\n")

        result = self.manager.image_exists("my-image:latest")

        assert result is False
        mock_run.assert_called_once_with(["container", "image", "list"], check=False)

    @patch("cjlib.container._run_command")
    def test_image_exists_returns_false_on_exception(self, mock_run):
        """Test that image_exists returns False when an exception occurs."""
        mock_run.side_effect = Exception("Some error")

        result = self.manager.image_exists("my-image")

        assert result is False

    @patch("cjlib.container._run_command")
    def test_run_interactive_success(self, mock_run):
        """Test successful interactive container run."""
        mock_run.return_value = Mock(returncode=0)

        exit_code = self.manager.run_interactive(
            image="my-image:latest",
            working_dir="/workspace",
            volume_mounts=["/host/path:/container/path", "/host/data:/data"],
            command=["bash", "-c", "echo hello"],
        )

        expected_cmd = [
            "container",
            "run",
            "-it",
            "--rm",
            "-v",
            "/host/path:/container/path",
            "-v",
            "/host/data:/data",
            "-w",
            "/workspace",
            "my-image:latest",
            "bash",
            "-c",
            "echo hello",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False, capture_output=False)
        assert exit_code == 0

    @patch("cjlib.container._run_command")
    def test_run_interactive_returns_exit_code(self, mock_run):
        """Test that run_interactive returns the container exit code."""
        mock_run.return_value = Mock(returncode=42)

        exit_code = self.manager.run_interactive(
            image="my-image",
            working_dir="/workspace",
            volume_mounts=[],
            command=["exit", "42"],
        )

        assert exit_code == 42

    @patch("cjlib.container._run_command")
    def test_run_interactive_with_no_mounts(self, mock_run):
        """Test run_interactive with no volume mounts."""
        mock_run.return_value = Mock(returncode=0)

        self.manager.run_interactive(
            image="my-image",
            working_dir="/workspace",
            volume_mounts=[],
            command=["ls"],
        )

        expected_cmd = [
            "container",
            "run",
            "-it",
            "--rm",
            "-w",
            "/workspace",
            "my-image",
            "ls",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False, capture_output=False)

    @patch("cjlib.container._run_command")
    def test_run_interactive_raises_on_exception(self, mock_run):
        """Test that run_interactive raises ContainerRunError on exception."""
        mock_run.side_effect = Exception("Failed to run")

        with pytest.raises(ContainerRunError, match="Failed to run container"):
            self.manager.run_interactive(
                image="my-image",
                working_dir="/workspace",
                volume_mounts=[],
                command=["bash"],
            )

    @patch("cjlib.container._run_command")
    def test_remove_image_success(self, mock_run):
        """Test successful image removal."""
        mock_run.return_value = Mock(returncode=0)

        self.manager.remove_image("my-image:latest")

        mock_run.assert_called_once_with(
            ["container", "image", "delete", "my-image:latest"], check=False
        )

    @patch("cjlib.container._run_command")
    def test_remove_image_ignores_errors(self, mock_run):
        """Test that remove_image doesn't raise errors."""
        mock_run.side_effect = Exception("Image not found")

        # Should not raise an exception
        self.manager.remove_image("non-existent-image")

        mock_run.assert_called_once_with(
            ["container", "image", "delete", "non-existent-image"], check=False
        )


class TestSetupSSHKeys:
    """Tests for setup_ssh_keys function."""

    def test_keys_already_exist(self, tmp_path):
        """Test that setup_ssh_keys does nothing if keys exist."""
        ssh_dir = tmp_path / "ssh"
        ssh_dir.mkdir()
        private_key = ssh_dir / "id_rsa"
        public_key = ssh_dir / "id_rsa.pub"
        private_key.write_text("private")
        public_key.write_text("public")

        with patch("cjlib.container._run_command") as mock_run:
            setup_ssh_keys(str(ssh_dir), str(private_key), str(public_key))

            # Should not call ssh-keygen
            mock_run.assert_not_called()

    @patch("cjlib.container._run_command")
    @patch("os.chmod")
    def test_generates_keys_when_missing(self, mock_chmod, mock_run, tmp_path):
        """Test that setup_ssh_keys generates keys when they don't exist."""
        ssh_dir = tmp_path / "ssh"
        private_key = ssh_dir / "id_rsa"
        public_key = ssh_dir / "id_rsa.pub"

        # Mock ssh-keygen to create the files
        def create_keys(*args, **kwargs):
            ssh_dir.mkdir(exist_ok=True)
            private_key.write_text("private")
            public_key.write_text("public")

        mock_run.side_effect = create_keys

        setup_ssh_keys(str(ssh_dir), str(private_key), str(public_key))

        # Verify ssh-keygen was called with correct parameters
        mock_run.assert_called_once_with(
            [
                "ssh-keygen",
                "-t",
                "rsa",
                "-b",
                "4096",
                "-f",
                str(private_key),
                "-N",
                "",
                "-C",
                "cj-container-access",
            ]
        )

        # Verify chmod was called to set permissions
        mock_chmod.assert_called_once_with(str(private_key), 0o600)

    @patch("cjlib.container._run_command")
    def test_creates_ssh_directory(self, mock_run, tmp_path):
        """Test that setup_ssh_keys creates SSH directory."""
        ssh_dir = tmp_path / "ssh"
        private_key = ssh_dir / "id_rsa"
        public_key = ssh_dir / "id_rsa.pub"

        # Mock ssh-keygen to create the files
        def create_keys(*args, **kwargs):
            private_key.write_text("private")
            public_key.write_text("public")

        mock_run.side_effect = create_keys

        setup_ssh_keys(str(ssh_dir), str(private_key), str(public_key))

        # Verify directory was created
        assert ssh_dir.exists()
        assert ssh_dir.is_dir()

    @patch("cjlib.container._run_command")
    def test_raises_on_keygen_failure(self, mock_run, tmp_path):
        """Test that setup_ssh_keys raises SSHKeyError on failure."""
        ssh_dir = tmp_path / "ssh"
        private_key = ssh_dir / "id_rsa"
        public_key = ssh_dir / "id_rsa.pub"

        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ssh-keygen", stderr="Key generation failed"
        )

        with pytest.raises(SSHKeyError) as exc_info:
            setup_ssh_keys(str(ssh_dir), str(private_key), str(public_key))

        assert "Failed to generate SSH keys" in str(exc_info.value)

    @patch("cjlib.container._run_command")
    @patch("os.chmod")
    def test_raises_on_chmod_failure(self, mock_chmod, mock_run, tmp_path):
        """Test that setup_ssh_keys raises SSHKeyError on chmod failure."""
        ssh_dir = tmp_path / "ssh"
        private_key = ssh_dir / "id_rsa"
        public_key = ssh_dir / "id_rsa.pub"

        # Mock ssh-keygen to create the files
        def create_keys(*args, **kwargs):
            ssh_dir.mkdir(exist_ok=True)
            private_key.write_text("private")
            public_key.write_text("public")

        mock_run.side_effect = create_keys
        mock_chmod.side_effect = OSError("Permission denied")

        with pytest.raises(SSHKeyError) as exc_info:
            setup_ssh_keys(str(ssh_dir), str(private_key), str(public_key))

        assert "Failed to set permissions on private key" in str(exc_info.value)
