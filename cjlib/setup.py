"""Setup mode implementation for CJ."""

import os
from cjlib.config import Config
from cjlib.container import ContainerManager
from cjlib.namegen import generate_name


# flake8: noqa: E501
CLAUDE_MD_TEMPLATE = """## Modifying Software Projects
- You MUST always validate that a project still builds after making changes.
- You MUST always run linting on a project after making changes.
- You MUST always fix linting errors and warnings.
- You MUST always run available tests on a project after making changes.
- You MUST always fix failing tests.
- You MUST NOT push to a remote git repository before making sure that README.md and Claude.md have been updated according to latest changes.

## Secure Coding
- You MUST NEVER implement logging of secrets like cryptographic keys, API keys, user names, or similar.
- You MUST NEVER add log files to git repositories.

## Documentation, README, Git commit messages
- When committing, always include a verbatim copy of the starting prompt used for this conversation.
- You MUST NOT boast about program features.
- When writing user-oriented documentation, do not talk about technical or architectural details which are irrelevant to the end user.
- Avoid using overly enthusiastic or boastful wording like "comprehensive", "excellent", "greatly" etc. Remain clear and factual.

## Rust
- Always reformat code with `cargo fmt` after making a change
- ALways lint code with `cargo clippy --allow-dirty --fix`. Then fix all the issues that were not yet fixed.
"""


class SetupCommand:
    """Implements the setup command for CJ."""

    def __init__(self, config: Config, container_mgr: ContainerManager):
        """Initialize SetupCommand.

        Args:
            config: Config instance for managing .cj directory
            container_mgr: ContainerManager instance for container operations
        """
        self.config = config
        self.container_mgr = container_mgr

    def _generate_claude_md(self, path: str) -> None:
        """Write CLAUDE.md template to specified path.

        Args:
            path: Path where CLAUDE.md should be written
        """
        with open(path, "w") as f:
            f.write(CLAUDE_MD_TEMPLATE)

    def _cleanup_on_failure(self) -> None:
        """Remove .cj directory on build failure."""
        try:
            self.config.cleanup()
        except Exception:
            # Silently ignore cleanup errors
            pass

    def run(self, extra_packages: list[str] = None) -> int:
        """Execute setup command.

        Args:
            extra_packages: Optional list of additional Ubuntu packages to install

        Returns:
            0 on success, 1 on failure
        """
        # Check if container setup already exists (Dockerfile present)
        if os.path.exists(self.config.get_dockerfile_path()):
            print("Error: Container setup already exists. Run 'cj update' to rebuild.")
            return 1

        # Check if container command is available
        if not self.container_mgr.check_container_available():
            print("Error: 'container' command not found. Please install macOS container tool.")
            return 1

        try:
            # Create config directory if it doesn't exist (it might exist from venv bootstrapping)
            os.makedirs(self.config.get_config_dir(), exist_ok=True)

            # Generate random image name
            image_name = generate_name()

            # Store extra packages if provided
            if extra_packages:
                self.config.write_extra_packages(extra_packages)
                print(f"Extra packages to install: {' '.join(extra_packages)}")

            # Write Dockerfile
            self.config.generate_and_write_dockerfile(extra_packages)
            dockerfile_path = self.config.get_dockerfile_path()
            print(f"Generated Dockerfile at {dockerfile_path}")

            # Write default CLAUDE.md if it doesn't exist
            context_dir = os.path.dirname(self.config.get_config_dir())
            claude_md_path = os.path.join(context_dir, "CLAUDE.md")
            if not os.path.exists(claude_md_path):
                self._generate_claude_md(claude_md_path)
                print(f"Generated default CLAUDE.md at {claude_md_path}")

            # Build container image
            print(f"Building container image '{image_name}'...")
            context_dir = os.path.dirname(self.config.get_config_dir())
            log_file = os.path.join(self.config.get_config_dir(), "build.log")
            self.container_mgr.build_image(dockerfile_path, image_name, context_dir, log_file)

            # Write image name to config
            self.config.write_image_name(image_name)
            print(f"Build log saved to {log_file}")

            print(f"Successfully created container image '{image_name}'")
            print("Run 'cj' to start Claude Code in the container")
            return 0

        except Exception as e:
            print(f"Error during setup: {e}")
            self._cleanup_on_failure()
            return 1
