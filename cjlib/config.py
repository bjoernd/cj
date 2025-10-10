"""Configuration management for .cj directory and its contents."""

import shutil
from pathlib import Path


# Dockerfile template for container setup
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

# Set working directory
WORKDIR /workspace

CMD ["/usr/bin/zsh"]
"""


# Constants
CONFIG_DIR = ".cj"
IMAGE_NAME_FILE = "image-name"
DOCKERFILE_NAME = "Dockerfile"
CLAUDE_DIR = "claude"
VENV_DIR = "venv"
EXTRA_PACKAGES_FILE = "extra-packages"


# Custom exceptions
class ConfigExistsError(Exception):
    """Raised when .cj directory already exists."""

    pass


class ConfigNotFoundError(Exception):
    """Raised when .cj directory doesn't exist."""

    pass


class ImageNameNotFoundError(Exception):
    """Raised when image-name file doesn't exist."""

    pass


class Config:
    """Configuration management for CJ project."""

    def __init__(self, base_dir: str = "."):
        """Initialize Config with base directory path.

        Args:
            base_dir: Base directory for the project (default: current directory)
        """
        self.base_dir = Path(base_dir).resolve()

    def get_config_dir(self) -> str:
        """Return full path to .cj directory.

        Returns:
            Absolute path to .cj directory
        """
        return str(self.base_dir / CONFIG_DIR)

    def exists(self) -> bool:
        """Check if .cj directory exists.

        Returns:
            True if .cj directory exists, False otherwise
        """
        return (self.base_dir / CONFIG_DIR).is_dir()

    def create_config_dir(self) -> None:
        """Create .cj directory.

        Raises:
            ConfigExistsError: If .cj directory already exists
        """
        config_path = self.base_dir / CONFIG_DIR
        if config_path.exists():
            raise ConfigExistsError(f"Configuration directory already exists: {config_path}")
        config_path.mkdir(parents=True, exist_ok=False)

    def get_image_name_path(self) -> str:
        """Return path to image-name file.

        Returns:
            Absolute path to image-name file
        """
        return str(self.base_dir / CONFIG_DIR / IMAGE_NAME_FILE)

    def read_image_name(self) -> str:
        """Read and return image name from file.

        Returns:
            Image name as string

        Raises:
            ImageNameNotFoundError: If image-name file doesn't exist
        """
        image_name_path = self.base_dir / CONFIG_DIR / IMAGE_NAME_FILE
        if not image_name_path.exists():
            raise ImageNameNotFoundError(f"Image name file not found: {image_name_path}")
        return image_name_path.read_text().strip()

    def write_image_name(self, name: str) -> None:
        """Write image name to file.

        Args:
            name: Image name to write
        """
        image_name_path = self.base_dir / CONFIG_DIR / IMAGE_NAME_FILE
        image_name_path.write_text(name)

    def get_dockerfile_path(self) -> str:
        """Return path to Dockerfile.

        Returns:
            Absolute path to Dockerfile
        """
        return str(self.base_dir / CONFIG_DIR / DOCKERFILE_NAME)

    def get_claude_dir(self) -> str:
        """Return path to .cj/claude directory.

        Returns:
            Absolute path to claude directory
        """
        return str(self.base_dir / CONFIG_DIR / CLAUDE_DIR)

    def ensure_claude_dir(self) -> None:
        """Create .cj/claude directory if it doesn't exist.

        This method is idempotent - it won't error if directory already exists.
        """
        claude_path = self.base_dir / CONFIG_DIR / CLAUDE_DIR
        claude_path.mkdir(parents=True, exist_ok=True)

    def get_venv_dir(self) -> str:
        """Return path to .cj/venv directory.

        Returns:
            Absolute path to venv directory
        """
        return str(self.base_dir / CONFIG_DIR / VENV_DIR)

    def write_extra_packages(self, packages: list[str]) -> None:
        """Write extra packages list to file.

        Args:
            packages: List of package names to write
        """
        extra_packages_path = self.base_dir / CONFIG_DIR / EXTRA_PACKAGES_FILE
        # Store packages as space-separated list
        extra_packages_path.write_text(" ".join(packages))

    def read_extra_packages(self) -> list[str]:
        """Read and return extra packages list from file.

        Returns:
            List of package names, empty list if file doesn't exist

        Raises:
            ConfigNotFoundError: If .cj directory doesn't exist
        """
        if not self.exists():
            raise ConfigNotFoundError(f"Configuration directory not found: {self.get_config_dir()}")

        extra_packages_path = self.base_dir / CONFIG_DIR / EXTRA_PACKAGES_FILE
        if not extra_packages_path.exists():
            return []

        content = extra_packages_path.read_text().strip()
        if not content:
            return []

        return content.split()

    def _extract_packages_from_dockerfile(self, dockerfile_content: str) -> set[str]:
        """Extract package names from apt-get install lines in Dockerfile.

        Args:
            dockerfile_content: Content of the Dockerfile

        Returns:
            Set of package names found in apt-get install commands
        """
        packages = set()
        lines = dockerfile_content.split("\n")
        in_apt_install = False

        for line in lines:
            stripped = line.strip()

            # Check if this line starts an apt-get install command
            if "apt-get install" in stripped:
                in_apt_install = True

            if in_apt_install:
                # Extract package names (skip flags like -y and line continuations)
                parts = stripped.split()
                for part in parts:
                    # Skip apt-get command itself, flags, and line continuations
                    if part not in ["RUN", "apt-get", "install", "-y", "&&", "\\"]:
                        # Remove trailing backslash if present
                        pkg = part.rstrip("\\").strip()
                        if pkg:
                            packages.add(pkg)

                # Check if line ends (no continuation)
                if not stripped.endswith("\\"):
                    in_apt_install = False

        return packages

    def _generate_dockerfile_with_packages(self, extra_packages: list[str]) -> str:
        """Generate Dockerfile content with extra packages added.

        Args:
            extra_packages: List of additional packages to install

        Returns:
            Dockerfile content as string
        """
        # Extract existing packages from template
        existing_packages = self._extract_packages_from_dockerfile(DOCKERFILE_TEMPLATE)

        # Filter out packages that are already in the template
        new_packages = [pkg for pkg in extra_packages if pkg not in existing_packages]

        if not new_packages:
            # No new packages to add, return template as-is
            return DOCKERFILE_TEMPLATE

        # Add new packages to the apt-get install line
        # Find the line with apt-get install and add packages there
        lines = DOCKERFILE_TEMPLATE.split("\n")
        result_lines = []
        in_apt_install = False
        install_block_lines = []

        for line in lines:
            stripped = line.strip()

            if "apt-get install" in stripped:
                in_apt_install = True
                install_block_lines = [line]
            elif in_apt_install:
                install_block_lines.append(line)
                if not stripped.endswith("\\"):
                    # End of apt-get install block
                    # Add new packages before the last line
                    for pkg in new_packages:
                        # Add each package with proper indentation and continuation
                        result_lines.append(f"    {pkg} \\")
                    # Append the collected install block lines
                    result_lines.extend(install_block_lines)
                    in_apt_install = False
                    install_block_lines = []
            else:
                result_lines.append(line)

        return "\n".join(result_lines)

    def generate_and_write_dockerfile(self, extra_packages: list[str] = None) -> None:
        """Generate and write Dockerfile to .cj directory.

        Args:
            extra_packages: Optional list of additional packages to install
        """
        if extra_packages:
            content = self._generate_dockerfile_with_packages(extra_packages)
        else:
            content = DOCKERFILE_TEMPLATE

        dockerfile_path = self.base_dir / CONFIG_DIR / DOCKERFILE_NAME
        dockerfile_path.write_text(content)

    def cleanup(self) -> None:
        """Remove .cj directory and all its contents (including venv).

        This is a destructive operation that removes the entire configuration.
        """
        config_path = self.base_dir / CONFIG_DIR
        if config_path.exists():
            shutil.rmtree(config_path)
