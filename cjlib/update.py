"""Update mode implementation for CJ."""

import os
import subprocess
from cjlib.config import Config, ConfigNotFoundError
from cjlib.container import ContainerManager
from cjlib.setup import DOCKERFILE_TEMPLATE


class UpdateCommand:
    """Implements the update command for CJ."""

    def __init__(self, config: Config, container_mgr: ContainerManager):
        """Initialize UpdateCommand.

        Args:
            config: Config instance for managing .cj directory
            container_mgr: ContainerManager instance for container operations
        """
        self.config = config
        self.container_mgr = container_mgr

    def _pull_base_image(self) -> None:
        """Pull latest base image from registry.

        Raises:
            subprocess.CalledProcessError: If pull command fails
        """
        subprocess.run(["container", "pull", "ubuntu:25.04"], check=True, capture_output=True)

    def _regenerate_dockerfile(self, path: str) -> None:
        """Write Dockerfile template to specified path.

        Args:
            path: Path where Dockerfile should be written
        """
        with open(path, "w") as f:
            f.write(DOCKERFILE_TEMPLATE)

    def run(self) -> int:
        """Execute update command.

        Returns:
            0 on success, 1 on failure
        """
        # Check if config exists
        if not self.config.exists():
            print("Error: .cj directory not found. Run 'cj setup' first.")
            return 1

        try:
            # Read existing image name
            image_name = self.config.read_image_name()

            # Regenerate Dockerfile (user customizations will not be retained)
            dockerfile_path = self.config.get_dockerfile_path()
            self._regenerate_dockerfile(dockerfile_path)
            print(f"Regenerated Dockerfile at {dockerfile_path}")

            # Pull latest base image
            print("Pulling latest base image ubuntu:25.04...")
            self._pull_base_image()

            # Rebuild container image with same tag
            print(f"Rebuilding container image '{image_name}'...")
            context_dir = os.path.dirname(self.config.get_config_dir())
            self.container_mgr.build_image(dockerfile_path, image_name, context_dir)

            print(f"Successfully updated container image '{image_name}'")
            print("Run 'cj' to start Claude Code in the updated container")
            return 0

        except ConfigNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except subprocess.CalledProcessError as e:
            print(f"Error pulling base image: {e}")
            return 1
        except Exception as e:
            print(f"Error during update: {e}")
            return 1
