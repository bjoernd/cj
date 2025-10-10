"""Shell mode implementation for CJ."""

import os
from cjlib.config import Config, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import ContainerManager


# Container paths
CONTAINER_CLAUDE_DIR = "/root/.claude"
CONTAINER_WORKSPACE = "/workspace"


class ShellCommand:
    """Implements the Shell command for CJ."""

    def __init__(self, config: Config, container_mgr: ContainerManager):
        """Initialize ShellCommand.

        Args:
            config: Config instance for managing .cj directory
            container_mgr: ContainerManager instance for container operations
        """
        self.config = config
        self.container_mgr = container_mgr

    def _get_volume_mounts(self) -> list[str]:
        """Get list of volume mount strings for container.

        Returns:
            List of volume mount strings in format "host:container" or "host:container:mode"
        """
        cwd = os.getcwd()
        claude_dir = self.config.get_claude_dir()
        config_dir = self.config.get_config_dir()

        return [
            f"{cwd}:{CONTAINER_WORKSPACE}",
            f"{config_dir}:{CONTAINER_WORKSPACE}/.cj:ro",  # Make .cj read-only
            f"{claude_dir}:{CONTAINER_CLAUDE_DIR}",  # Keep credentials writable
        ]

    def run(self) -> int:
        """Execute Shell command.

        Returns:
            0 on success, 1 on failure, or container exit code
        """
        # Check if config exists
        if not self.config.exists():
            print("Error: .cj directory not found. Run 'cj setup' first.")
            return 1

        try:
            # Read image name from config
            image_name = self.config.read_image_name()

            # Check if image exists
            if not self.container_mgr.image_exists(image_name):
                print(f"Error: Container image '{image_name}' not found. Run 'cj setup' first.")
                return 1

            # Ensure .cj/claude directory exists for credential persistence
            self.config.ensure_claude_dir()

            # Get volume mounts
            volume_mounts = self._get_volume_mounts()

            # Prepare environment variables (preserve TERM for color support)
            env_vars = []
            term_value = os.environ.get("TERM", "xterm-256color")
            env_vars.append(f"TERM={term_value}")

            # Run container interactively with bash
            exit_code = self.container_mgr.run_interactive(
                image=image_name,
                working_dir=CONTAINER_WORKSPACE,
                volume_mounts=volume_mounts,
                command=["/bin/bash"],
                env_vars=env_vars,
            )

            return exit_code

        except (ConfigNotFoundError, ImageNameNotFoundError) as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error running shell: {e}")
            return 1
