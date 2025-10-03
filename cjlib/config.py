"""Configuration management for .cj directory and its contents."""

import shutil
from pathlib import Path


# Constants
CONFIG_DIR = ".cj"
IMAGE_NAME_FILE = "image-name"
DOCKERFILE_NAME = "Dockerfile"
CLAUDE_DIR = "claude"
VENV_DIR = "venv"
SSH_DIR = "ssh"
SSH_PRIVATE_KEY = "id_rsa"
SSH_PUBLIC_KEY = "id_rsa.pub"
BROWSER_BRIDGE_PORT = 9999


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

    def get_ssh_dir(self) -> str:
        """Return path to .cj/ssh directory.

        Returns:
            Absolute path to ssh directory
        """
        return str(self.base_dir / CONFIG_DIR / SSH_DIR)

    def ensure_ssh_dir(self) -> None:
        """Create .cj/ssh directory if it doesn't exist.

        This method is idempotent - it won't error if directory already exists.
        """
        ssh_path = self.base_dir / CONFIG_DIR / SSH_DIR
        ssh_path.mkdir(parents=True, exist_ok=True)

    def get_ssh_private_key_path(self) -> str:
        """Return path to SSH private key.

        Returns:
            Absolute path to SSH private key
        """
        return str(self.base_dir / CONFIG_DIR / SSH_DIR / SSH_PRIVATE_KEY)

    def get_ssh_public_key_path(self) -> str:
        """Return path to SSH public key.

        Returns:
            Absolute path to SSH public key
        """
        return str(self.base_dir / CONFIG_DIR / SSH_DIR / SSH_PUBLIC_KEY)

    def cleanup(self) -> None:
        """Remove .cj directory and all its contents (including venv).

        This is a destructive operation that removes the entire configuration.
        """
        config_path = self.base_dir / CONFIG_DIR
        if config_path.exists():
            shutil.rmtree(config_path)
