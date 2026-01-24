"""Proxy management for network filtering via Squid."""

import shutil
import socket
import subprocess
import time
from pathlib import Path


# Custom exceptions
class ProxyNotAvailableError(Exception):
    """Raised when Squid proxy is not available."""

    pass


class ProxyNotRunningError(Exception):
    """Raised when Squid proxy is not running."""

    pass


# Default domains that are allowed through the proxy
DEFAULT_ALLOWLIST = [
    "api.anthropic.com",
    "github.com",
    ".github.com",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "crates.io",
    "static.crates.io",
    "rustup.rs",
    "static.rust-lang.org",
]

# Constants
NETWORK_ALLOWLIST_FILE = "network-allowlist"
NETWORK_FILTER_ENABLED_FILE = "network-filter-enabled"
SQUID_CONFIG_FILE = "squid.conf"
SQUID_PORT = 3128


class ProxyManager:
    """Manager for Squid proxy operations."""

    def __init__(self, config_dir: str):
        """Initialize ProxyManager.

        Args:
            config_dir: Path to .cj configuration directory
        """
        self.config_dir = Path(config_dir)

    def check_squid_installed(self) -> bool:
        """Check if Squid is installed.

        Returns:
            True if squid command is available, False otherwise
        """
        return shutil.which("squid") is not None

    def check_squid_running(self, port: int = SQUID_PORT) -> bool:
        """Check if Squid is running by testing connection to proxy port.

        Args:
            port: Port to check (default: 3128)

        Returns:
            True if connection succeeds, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.connect(("127.0.0.1", port))
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

    def detect_host_ip(self) -> str:
        """Auto-detect the host IP address for the proxy.

        Tries ipconfig getifaddr en0 first, falls back to common gateway.

        Returns:
            IP address string
        """
        try:
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en0"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback to common container gateway
        return "192.168.65.1"

    def get_proxy_url(self, host_override: str = None) -> str:
        """Get the proxy URL.

        Args:
            host_override: Optional host IP to use instead of auto-detection

        Returns:
            Proxy URL string (e.g., "http://192.168.1.100:3128")
        """
        host = host_override if host_override else self.detect_host_ip()
        return f"http://{host}:{SQUID_PORT}"

    def _get_allowlist_path(self) -> Path:
        """Get path to allowlist file."""
        return self.config_dir / NETWORK_ALLOWLIST_FILE

    def read_allowlist(self) -> list[str]:
        """Read allowlist from file.

        Returns:
            List of allowed domains, or DEFAULT_ALLOWLIST if file doesn't exist
        """
        allowlist_path = self._get_allowlist_path()
        if not allowlist_path.exists():
            return DEFAULT_ALLOWLIST.copy()

        content = allowlist_path.read_text()
        domains = [line.strip() for line in content.split("\n") if line.strip()]
        return domains

    def write_allowlist(self, domains: list[str]) -> None:
        """Write allowlist to file.

        Args:
            domains: List of domains to allow
        """
        allowlist_path = self._get_allowlist_path()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        allowlist_path.write_text("\n".join(domains) + "\n")

    def merge_allowlist(self, new_domains: list[str]) -> None:
        """Merge new domains with existing allowlist.

        Args:
            new_domains: New domains to add
        """
        existing = self.read_allowlist()
        # Deduplicate and sort
        merged = sorted(set(existing + new_domains))
        self.write_allowlist(merged)

    def _get_squid_config_path(self) -> Path:
        """Get path to Squid config file."""
        return self.config_dir / SQUID_CONFIG_FILE

    def generate_squid_config(self) -> str:
        """Generate Squid configuration content.

        Returns:
            Squid configuration as string
        """
        allowlist_path = self._get_allowlist_path()

        config = f"""# CJ Network Filter - Auto-generated
http_port {SQUID_PORT}

# Allowed domains
acl cj_allowed dstdomain "{allowlist_path}"

# Standard port restrictions
acl SSL_ports port 443
acl Safe_ports port 80 443

# Access rules
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow cj_allowed
http_access deny all
"""
        return config

    def write_squid_config(self) -> None:
        """Write Squid configuration to file.

        Ensures the allowlist file exists with defaults before writing config.
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Ensure allowlist file exists (Squid config references it)
        allowlist_path = self._get_allowlist_path()
        if not allowlist_path.exists():
            self.write_allowlist(DEFAULT_ALLOWLIST)

        config_path = self._get_squid_config_path()
        config_path.write_text(self.generate_squid_config())

    def _get_filter_enabled_path(self) -> Path:
        """Get path to filter enabled file."""
        return self.config_dir / NETWORK_FILTER_ENABLED_FILE

    def is_filter_enabled(self) -> bool:
        """Check if network filtering is enabled.

        Returns:
            True if filtering is enabled, False otherwise
        """
        enabled_path = self._get_filter_enabled_path()
        if not enabled_path.exists():
            return False
        return enabled_path.read_text().strip().lower() == "true"

    def set_filter_enabled(self, enabled: bool) -> None:
        """Set network filtering enabled state.

        Args:
            enabled: True to enable, False to disable
        """
        enabled_path = self._get_filter_enabled_path()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        enabled_path.write_text("true" if enabled else "false")

    def get_proxy_env_vars(self, host_override: str = None) -> list[str]:
        """Get proxy environment variables for container.

        Args:
            host_override: Optional host IP to use instead of auto-detection

        Returns:
            List of environment variable strings (e.g., ["HTTP_PROXY=..."])
        """
        proxy_url = self.get_proxy_url(host_override)
        return [
            f"HTTP_PROXY={proxy_url}",
            f"HTTPS_PROXY={proxy_url}",
            f"http_proxy={proxy_url}",
            f"https_proxy={proxy_url}",
        ]

    def reload_squid(self) -> None:
        """Send reconfigure signal to Squid."""
        subprocess.run(
            ["squid", "-k", "reconfigure"],
            capture_output=True,
            text=True,
            check=False,
        )

    def start_squid(self) -> None:
        """Start Squid with our configuration.

        This starts Squid as a background process using our config file.
        """
        config_path = self._get_squid_config_path()

        # If already running, just reload
        if self.check_squid_running():
            self.reload_squid()
            return

        # Start Squid with our config
        subprocess.Popen(
            ["squid", "-f", str(config_path), "-N"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for Squid to start (up to 5 seconds)
        for _ in range(10):
            if self.check_squid_running():
                return
            time.sleep(0.5)

    def stop_squid(self) -> None:
        """Stop Squid."""
        subprocess.run(
            ["squid", "-k", "shutdown"],
            capture_output=True,
            text=True,
            check=False,
        )

    def ensure_available(self) -> None:
        """Ensure Squid is installed and available.

        Raises:
            ProxyNotAvailableError: If Squid is not installed
        """
        if not self.check_squid_installed():
            raise ProxyNotAvailableError(
                "Squid proxy is not installed. Install with: brew install squid"
            )
