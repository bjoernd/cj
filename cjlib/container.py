"""Container operations wrapper for macOS container command."""

import os
import subprocess
import shutil
from pathlib import Path
from typing import List


# Custom exceptions
class ContainerNotAvailableError(Exception):
    """Raised when container command is not available."""

    pass


class ContainerBuildError(Exception):
    """Raised when container build fails."""

    pass


class ContainerRunError(Exception):
    """Raised when container run fails."""

    pass


class SSHKeyError(Exception):
    """Raised when SSH key generation or setup fails."""

    pass


class SSHTunnelError(Exception):
    """Raised when SSH tunnel establishment fails."""

    pass


class SSHConnectionError(Exception):
    """Raised when SSH connection to container fails."""

    pass


def _run_command(
    args: List[str], check: bool = True, capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Execute a command using subprocess.run().

    Args:
        args: Command and arguments as a list
        check: If True, raise CalledProcessError on non-zero exit
        capture_output: If True, capture stdout and stderr

    Returns:
        CompletedProcess object containing the result
    """
    return subprocess.run(args, check=check, capture_output=capture_output, text=True)


def setup_ssh_keys(ssh_dir: str, private_key_path: str, public_key_path: str) -> None:
    """Generate SSH key pair for host if it doesn't exist.

    Args:
        ssh_dir: Path to SSH directory (.cj/ssh)
        private_key_path: Path where private key should be stored
        public_key_path: Path where public key should be stored

    Raises:
        SSHKeyError: If SSH key generation fails
    """
    # Check if keys already exist
    private_key = Path(private_key_path)
    public_key = Path(public_key_path)

    if private_key.exists() and public_key.exists():
        # Keys already exist, nothing to do
        return

    # Ensure SSH directory exists
    ssh_path = Path(ssh_dir)
    ssh_path.mkdir(parents=True, exist_ok=True)

    # Generate SSH key pair
    try:
        _run_command(
            [
                "ssh-keygen",
                "-t",
                "rsa",
                "-b",
                "4096",
                "-f",
                private_key_path,
                "-N",
                "",
                "-C",
                "cj-container-access",
            ]
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to generate SSH keys: {e}"
        if e.stderr:
            error_msg += f"\n{e.stderr}"
        raise SSHKeyError(error_msg) from e

    # Set proper permissions on private key (600)
    try:
        os.chmod(private_key_path, 0o600)
    except OSError as e:
        raise SSHKeyError(f"Failed to set permissions on private key: {e}") from e


class ContainerManager:
    """Manager for macOS container command operations."""

    def check_container_available(self) -> bool:
        """Check if the container command is available.

        Returns:
            bool: True if container command exists, False otherwise
        """
        return shutil.which("container") is not None

    def build_image(
        self, dockerfile_path: str, tag: str, context_dir: str, log_file: str = None
    ) -> None:
        """Build a container image.

        Args:
            dockerfile_path: Path to the Dockerfile
            tag: Tag name for the image
            context_dir: Build context directory
            log_file: Optional path to log file for build output

        Raises:
            ContainerBuildError: If the build fails
        """
        try:
            result = _run_command(
                ["container", "build", "-t", tag, "-f", dockerfile_path, context_dir]
            )
            if log_file:
                with open(log_file, "w") as f:
                    if result.stdout:
                        f.write(result.stdout)
                    if result.stderr:
                        f.write(result.stderr)
        except subprocess.CalledProcessError as e:
            error_msg = "Failed to build image"
            if e.stderr:
                error_msg += f"\nError output:\n{e.stderr}"
            if e.stdout:
                error_msg += f"\nOutput:\n{e.stdout}"
            if log_file:
                with open(log_file, "w") as f:
                    if e.stdout:
                        f.write(e.stdout)
                    if e.stderr:
                        f.write(e.stderr)
            raise ContainerBuildError(error_msg) from e

    def image_exists(self, tag: str) -> bool:
        """Check if a container image exists.

        Args:
            tag: Tag name to check for

        Returns:
            bool: True if image exists, False otherwise
        """
        try:
            result = _run_command(["container", "image", "list"], check=False)
            return tag in result.stdout
        except Exception:
            return False

    def run_interactive(
        self,
        image: str,
        working_dir: str,
        volume_mounts: List[str],
        command: List[str],
        port_forwards: List[tuple] = None,
    ) -> int:
        """Run a container interactively.

        Args:
            image: Image name/tag to run
            working_dir: Working directory inside container
            volume_mounts: List of volume mount strings (format: "host:container")
            command: Command to execute in the container
            port_forwards: Optional list of (host_port, container_port) tuples for port forwarding

        Returns:
            int: Exit code from the container

        Raises:
            ContainerRunError: If the container fails to run
        """
        # Build the command
        cmd = ["container", "run", "-it", "--rm"]

        # Add port forwards
        if port_forwards:
            for host_port, container_port in port_forwards:
                cmd.extend(["-p", f"{host_port}:{container_port}"])

        # Add volume mounts
        for mount in volume_mounts:
            cmd.extend(["-v", mount])

        # Add working directory
        cmd.extend(["-w", working_dir])

        # Add image
        cmd.append(image)

        # Add command to execute
        cmd.extend(command)

        try:
            result = _run_command(cmd, check=False, capture_output=False)
            return result.returncode
        except Exception as e:
            raise ContainerRunError(f"Failed to run container: {e}") from e

    def remove_image(self, tag: str) -> None:
        """Remove a container image.

        Args:
            tag: Tag name of the image to remove

        Note:
            Does not raise an error if the image doesn't exist
        """
        try:
            _run_command(["container", "image", "delete", tag], check=False)
        except Exception:
            # Ignore errors (e.g., image doesn't exist)
            pass

    def setup_reverse_tunnel(
        self,
        ssh_private_key_path: str,
        ssh_port: int = 2222,
        forward_port: int = 9999,
    ) -> subprocess.Popen:
        """Establish SSH reverse tunnel to container.

        Args:
            ssh_private_key_path: Path to SSH private key for authentication
            ssh_port: Port on host where container's SSH is forwarded (default: 2222)
            forward_port: Port to forward from container to host (default: 9999)

        Returns:
            subprocess.Popen: Process object for the SSH tunnel

        Raises:
            SSHTunnelError: If tunnel establishment fails
        """
        # Build SSH command for reverse tunnel
        # -R forward_port:localhost:forward_port = reverse tunnel
        # -N = no command execution
        # -o StrictHostKeyChecking=no = don't prompt for host key verification
        # -o UserKnownHostsFile=/dev/null = don't save host key
        cmd = [
            "ssh",
            "-R",
            f"{forward_port}:localhost:{forward_port}",
            "-p",
            str(ssh_port),
            "-i",
            ssh_private_key_path,
            "-N",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "root@localhost",
        ]

        try:
            # Start SSH tunnel in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            return process
        except Exception as e:
            raise SSHTunnelError(f"Failed to establish SSH tunnel: {e}") from e
