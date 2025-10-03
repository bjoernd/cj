"""Claude mode implementation for CJ."""

import os
import time
import threading
from cjlib.config import Config, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import ContainerManager, setup_ssh_keys
from cjlib.setup import SetupCommand
from cjlib.browser_bridge import BrowserBridge


# Container paths
CONTAINER_CLAUDE_DIR = "/root/.claude"
CONTAINER_WORKSPACE = "/workspace"
CONTAINER_SSH_DIR = "/tmp/host-ssh"

# SSH and bridge ports
SSH_FORWARD_PORT = 2222
BROWSER_BRIDGE_PORT = 9999


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
        ssh_dir = self.config.get_ssh_dir()

        return [
            f"{cwd}:{CONTAINER_WORKSPACE}",
            f"{claude_dir}:{CONTAINER_CLAUDE_DIR}",
            f"{ssh_dir}:{CONTAINER_SSH_DIR}",
        ]

    def _get_path_mappings(self, volume_mounts: list[str]) -> list[tuple]:
        """Create path mappings for file:// URL translation.

        Args:
            volume_mounts: List of volume mount strings in format "host:container"

        Returns:
            List of (container_path, host_path) tuples for URL translation
        """
        path_mappings = []
        for mount in volume_mounts:
            host_path, container_path = mount.split(":")
            # Skip temporary mounts (not useful for URL translation)
            if not container_path.startswith("/tmp"):
                path_mappings.append((container_path, host_path))
        return path_mappings

    def _setup_ssh_tunnel(self, ssh_private_key_path: str):
        """Setup SSH tunnel in a separate thread after waiting for SSH to be ready.

        Args:
            ssh_private_key_path: Path to SSH private key

        Returns:
            Tuple of (tunnel_process, thread) for cleanup
        """
        tunnel_process = None
        tunnel_ready = threading.Event()

        def establish_tunnel():
            nonlocal tunnel_process
            # Wait for SSH daemon to be ready in container
            time.sleep(2)

            try:
                tunnel_process = self.container_mgr.setup_reverse_tunnel(
                    ssh_private_key_path=ssh_private_key_path,
                    ssh_port=SSH_FORWARD_PORT,
                    forward_port=BROWSER_BRIDGE_PORT,
                )
                tunnel_ready.set()
            except Exception as e:
                print(f"Warning: Failed to establish SSH tunnel: {e}")
                print("Browser redirection will not be available.")
                tunnel_ready.set()

        tunnel_thread = threading.Thread(target=establish_tunnel, daemon=True)
        tunnel_thread.start()

        # Wait for tunnel to be established (or fail)
        tunnel_ready.wait(timeout=5)

        return tunnel_process, tunnel_thread

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

        browser_bridge = None
        tunnel_process = None

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

            # Setup SSH keys for browser redirection
            self.config.ensure_ssh_dir()
            ssh_private_key = self.config.get_ssh_private_key_path()
            ssh_public_key = self.config.get_ssh_public_key_path()

            try:
                setup_ssh_keys(
                    self.config.get_ssh_dir(),
                    ssh_private_key,
                    ssh_public_key,
                )
            except Exception as e:
                print(f"Warning: Failed to setup SSH keys: {e}")
                print("Browser redirection will not be available.")

            # Get volume mounts
            volume_mounts = self._get_volume_mounts()

            # Create path mappings for browser bridge
            path_mappings = self._get_path_mappings(volume_mounts)

            # Start browser bridge
            browser_bridge = BrowserBridge(port=BROWSER_BRIDGE_PORT, path_mappings=path_mappings)
            browser_bridge.start()

            # Setup SSH tunnel in background thread
            tunnel_process, tunnel_thread = self._setup_ssh_tunnel(ssh_private_key)

            # Run container interactively with port forwarding
            exit_code = self.container_mgr.run_interactive(
                image=image_name,
                working_dir=CONTAINER_WORKSPACE,
                volume_mounts=volume_mounts,
                command=["claude"],
                port_forwards=[(str(SSH_FORWARD_PORT), "22")],
            )

            return exit_code

        except (ConfigNotFoundError, ImageNameNotFoundError) as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error running Claude Code: {e}")
            return 1
        finally:
            # Cleanup: stop tunnel and browser bridge
            if tunnel_process:
                try:
                    tunnel_process.terminate()
                    tunnel_process.wait(timeout=2)
                except Exception:
                    pass

            if browser_bridge:
                try:
                    browser_bridge.stop()
                except Exception:
                    pass
