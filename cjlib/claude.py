"""Claude mode implementation for CJ."""

import os
from cjlib.config import Config, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import ContainerManager
from cjlib.setup import SetupCommand


# Container paths
CONTAINER_CLAUDE_DIR = "/root/.claude"
CONTAINER_WORKSPACE = "/workspace"


class ClaudeCommand:
    """Implements the Claude command for CJ."""

    def __init__(self, config: Config, container_mgr: ContainerManager, setup_cmd: SetupCommand):
        """Initialize ClaudeCommand.

        Args:
            config: Config instance for managing .cj directory
            container_mgr: ContainerManager instance for container operations
            setup_cmd: SetupCommand instance for rebuilding image if needed
        """
        self.config = config
        self.container_mgr = container_mgr
        self.setup_cmd = setup_cmd

    def _get_volume_mounts(self) -> list[str]:
        """Get list of volume mount strings for container.

        Returns:
            List of volume mount strings in format "host:container"
        """
        cwd = os.getcwd()
        claude_dir = self.config.get_claude_dir()

        return [f"{cwd}:{CONTAINER_WORKSPACE}", f"{claude_dir}:{CONTAINER_CLAUDE_DIR}"]

    def _rebuild_image(self) -> None:
        """Rebuild container image using setup command."""
        print("Container image not found. Rebuilding...")
        result = self.setup_cmd.run()
        if result != 0:
            raise Exception("Failed to rebuild container image")

    def run(self) -> int:
        """Execute Claude command.

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
                self._rebuild_image()
                # Re-read image name after rebuild
                image_name = self.config.read_image_name()

            # Ensure .cj/claude directory exists for credential persistence
            self.config.ensure_claude_dir()

            # Get volume mounts
            volume_mounts = self._get_volume_mounts()

            # Run container interactively
            exit_code = self.container_mgr.run_interactive(
                image=image_name,
                working_dir=CONTAINER_WORKSPACE,
                volume_mounts=volume_mounts,
                command=["claude"],
            )

            return exit_code

        except (ConfigNotFoundError, ImageNameNotFoundError) as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error running Claude Code: {e}")
            return 1
