"""Update mode implementation for CJ."""

import os
from cjlib.config import Config, ConfigNotFoundError
from cjlib.container import ContainerManager


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

    def run(self, extra_packages: list[str] = None) -> int:
        """Execute update command.

        Args:
            extra_packages: Optional list of additional Ubuntu packages to install

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

            # Read stored extra packages and merge with new ones
            stored_packages = self.config.read_extra_packages()

            if extra_packages:
                # Merge new packages with stored ones, keeping unique packages
                all_packages = list(set(stored_packages + extra_packages))
                # Sort for consistent ordering
                all_packages.sort()

                # Save updated package list
                self.config.write_extra_packages(all_packages)
                print(f"Extra packages to install: {' '.join(all_packages)}")
            else:
                all_packages = stored_packages
                if all_packages:
                    print(f"Extra packages to install: {' '.join(all_packages)}")

            # Regenerate Dockerfile (user customizations will not be retained)
            self.config.generate_and_write_dockerfile(all_packages if all_packages else None)
            dockerfile_path = self.config.get_dockerfile_path()
            print(f"Regenerated Dockerfile at {dockerfile_path}")

            # Rebuild container image with same tag (will use latest base image)
            print(f"Rebuilding container image '{image_name}'...")
            context_dir = os.path.dirname(self.config.get_config_dir())
            log_file = os.path.join(self.config.get_config_dir(), "update.log")
            self.container_mgr.build_image(dockerfile_path, image_name, context_dir, log_file)

            print(f"Successfully updated container image '{image_name}'")
            print(f"Update log saved to {log_file}")
            print("Run 'cj' to start Claude Code in the updated container")
            return 0

        except ConfigNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error during update: {e}")
            return 1
