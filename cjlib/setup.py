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
    vim neovim \\
    zsh \\
    curl \\
    git \\
    openssh-server \\
    netcat-openbsd \\
    && rm -rf /var/lib/apt/lists/*

# Install Python development tools via pip
RUN python3 -m pip install --break-system-packages pytest black flake8

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

# Create symlink for .claude.json to persist state in mounted .claude directory
RUN ln -s /root/.claude/.claude.json /root/.claude.json

# Configure SSH server
RUN mkdir -p /var/run/sshd /root/.ssh && \\
    chmod 700 /root/.ssh && \\
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin prohibit-password/' \\
        /etc/ssh/sshd_config && \\
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Create SSH initialization script
RUN echo '#!/bin/bash\\n\\
mkdir -p /root/.ssh\\n\\
if [ -f /tmp/host-ssh/id_rsa.pub ]; then\\n\\
  cat /tmp/host-ssh/id_rsa.pub > /root/.ssh/authorized_keys\\n\\
  chmod 600 /root/.ssh/authorized_keys\\n\\
  chmod 700 /root/.ssh\\n\\
fi\\n\\
exec /usr/sbin/sshd -D' > /usr/local/bin/init-ssh.sh && \\
    chmod +x /usr/local/bin/init-ssh.sh

# Create browser wrapper script that forwards URLs to host
RUN echo '#!/bin/bash\\n\\
PORT=9999\\n\\
URL="$*"\\n\\
echo "$URL" | nc -w 1 localhost $PORT 2>/dev/null\\n\\
exit 0' > /usr/local/bin/open && \\
    chmod +x /usr/local/bin/open

# Set BROWSER environment variable to use wrapper
ENV BROWSER=/usr/local/bin/open

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

            # Write Dockerfile
            dockerfile_path = self.config.get_dockerfile_path()
            self._generate_dockerfile(dockerfile_path)
            print(f"Generated Dockerfile at {dockerfile_path}")

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
