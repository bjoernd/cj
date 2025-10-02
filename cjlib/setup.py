"""Setup mode implementation for CJ."""

import os
from cjlib.config import Config
from cjlib.container import ContainerManager
from cjlib.namegen import generate_name


DOCKERFILE_TEMPLATE = """FROM ubuntu:25.04

# Update package lists and install development tools
RUN apt-get update && apt-get install -y \\
    gcc g++ \\
    clang \\
    python3 python3-dev python3-pip python3-venv \\
    python3-pytest python3-black \\
    vim neovim \\
    zsh \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Install Rust via rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \\
    --default-toolchain stable --profile default
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustc --version && cargo --version

# Install Node.js (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \\
    apt-get install -y nodejs && \\
    rm -rf /var/lib/apt/lists/*

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL \\
    https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \\
    "" --unattended

# Set zsh as default shell
RUN chsh -s $(which zsh)
ENV SHELL=/usr/bin/zsh

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Set working directory
WORKDIR /workspace

CMD ["/usr/bin/zsh"]
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

    def _generate_dockerfile(self, path: str) -> None:
        """Write Dockerfile template to specified path.

        Args:
            path: Path where Dockerfile should be written
        """
        with open(path, "w") as f:
            f.write(DOCKERFILE_TEMPLATE)

    def _cleanup_on_failure(self) -> None:
        """Remove .cj directory on build failure."""
        try:
            self.config.cleanup()
        except Exception:
            # Silently ignore cleanup errors
            pass

    def run(self) -> int:
        """Execute setup command.

        Returns:
            0 on success, 1 on failure
        """
        # Check if config already exists
        if self.config.exists():
            print("Error: .cj directory already exists. Run 'cj update' to rebuild.")
            return 1

        # Check if container command is available
        if not self.container_mgr.check_container_available():
            print("Error: 'container' command not found. Please install macOS container tool.")
            return 1

        try:
            # Create config directory
            self.config.create_config_dir()

            # Generate random image name
            image_name = generate_name()

            # Write Dockerfile
            dockerfile_path = self.config.get_dockerfile_path()
            self._generate_dockerfile(dockerfile_path)
            print(f"Generated Dockerfile at {dockerfile_path}")

            # Build container image
            print(f"Building container image '{image_name}'...")
            context_dir = os.path.dirname(self.config.get_config_dir())
            self.container_mgr.build_image(dockerfile_path, image_name, context_dir)

            # Write image name to config
            self.config.write_image_name(image_name)

            print(f"Successfully created container image '{image_name}'")
            print("Run 'cj' to start Claude Code in the container")
            return 0

        except Exception as e:
            print(f"Error during setup: {e}")
            self._cleanup_on_failure()
            return 1
