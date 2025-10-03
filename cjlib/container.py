"""Container operations wrapper for macOS container command."""

import subprocess
import shutil
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
    ) -> int:
        """Run a container interactively.

        Args:
            image: Image name/tag to run
            working_dir: Working directory inside container
            volume_mounts: List of volume mount strings (format: "host:container")
            command: Command to execute in the container

        Returns:
            int: Exit code from the container

        Raises:
            ContainerRunError: If the container fails to run
        """
        # Build the command
        cmd = ["container", "run", "-it", "--rm"]

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
