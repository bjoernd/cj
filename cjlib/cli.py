"""CLI argument parsing and command routing."""

import argparse
import sys
from cjlib.config import Config, ConfigExistsError, ConfigNotFoundError, ImageNameNotFoundError
from cjlib.container import (
    ContainerManager,
    ContainerNotAvailableError,
    ContainerBuildError,
    ContainerRunError,
)
from cjlib.proxy import ProxyManager, ProxyNotAvailableError
from cjlib.setup import SetupCommand
from cjlib.update import UpdateCommand
from cjlib.claude import ClaudeCommand
from cjlib.shell import ShellCommand


def main():
    """Main entry point for CJ CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="CJ (Claude Jailer) - Run Claude Code in an isolated container"
    )

    # Global arguments for default command (claude mode)
    parser.add_argument(
        "--filter-network",
        action="store_true",
        help="Enable network filtering via Squid proxy (persists)",
    )
    parser.add_argument(
        "--no-filter-network",
        action="store_true",
        help="Disable network filtering (persists)",
    )
    parser.add_argument(
        "--proxy-host",
        type=str,
        help="Override auto-detected host IP for proxy URL",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup subcommand
    setup_parser = subparsers.add_parser(
        "setup", help="Create project configuration and build container image"
    )
    setup_parser.add_argument(
        "--extra-packages",
        type=str,
        help="Whitespace-separated list of additional Ubuntu packages to install",
    )
    setup_parser.add_argument(
        "--allowed-domains",
        type=str,
        help="Whitespace-separated domains to allow (creates allowlist)",
    )
    setup_parser.add_argument(
        "--filter-network",
        action="store_true",
        help="Enable network filtering via Squid proxy",
    )

    # Update subcommand
    update_parser = subparsers.add_parser(
        "update", help="Rebuild container image with latest base image"
    )
    update_parser.add_argument(
        "--extra-packages",
        type=str,
        help="Whitespace-separated list of additional Ubuntu packages to install",
    )
    update_parser.add_argument(
        "--allowed-domains",
        type=str,
        help="Whitespace-separated domains to add to allowlist",
    )

    # Shell subcommand
    shell_parser = subparsers.add_parser("shell", help="Run interactive bash shell in container")
    shell_parser.add_argument(
        "--filter-network",
        action="store_true",
        help="Enable network filtering via Squid proxy (persists)",
    )
    shell_parser.add_argument(
        "--no-filter-network",
        action="store_true",
        help="Disable network filtering (persists)",
    )
    shell_parser.add_argument(
        "--proxy-host",
        type=str,
        help="Override auto-detected host IP for proxy URL",
    )

    args = parser.parse_args()

    # Instantiate dependencies
    config = Config()
    container_mgr = ContainerManager()
    proxy_mgr = ProxyManager(config.get_config_dir())

    try:
        # Route to appropriate command
        if args.command == "setup":
            # Parse extra packages if provided
            extra_packages = None
            if hasattr(args, "extra_packages") and args.extra_packages:
                extra_packages = args.extra_packages.split()

            # Parse allowed domains if provided
            allowed_domains = None
            if hasattr(args, "allowed_domains") and args.allowed_domains:
                allowed_domains = args.allowed_domains.split()

            # Check for filter-network flag
            filter_network = getattr(args, "filter_network", False)

            setup_cmd = SetupCommand(config, container_mgr, proxy_mgr)
            return setup_cmd.run(extra_packages, allowed_domains, filter_network)

        elif args.command == "update":
            # Parse extra packages if provided
            extra_packages = None
            if hasattr(args, "extra_packages") and args.extra_packages:
                extra_packages = args.extra_packages.split()

            # Parse allowed domains if provided
            allowed_domains = None
            if hasattr(args, "allowed_domains") and args.allowed_domains:
                allowed_domains = args.allowed_domains.split()

            update_cmd = UpdateCommand(config, container_mgr, proxy_mgr)
            return update_cmd.run(extra_packages, allowed_domains)

        elif args.command == "shell":
            # Handle --filter-network / --no-filter-network
            filter_network = getattr(args, "filter_network", False)
            no_filter_network = getattr(args, "no_filter_network", False)
            proxy_host = getattr(args, "proxy_host", None)

            if filter_network:
                proxy_mgr.set_filter_enabled(True)
            elif no_filter_network:
                proxy_mgr.set_filter_enabled(False)

            shell_cmd = ShellCommand(config, container_mgr, proxy_mgr)
            return shell_cmd.run(proxy_host)

        else:
            # Default: Claude mode (no subcommand)
            # Handle --filter-network / --no-filter-network
            filter_network = getattr(args, "filter_network", False)
            no_filter_network = getattr(args, "no_filter_network", False)
            proxy_host = getattr(args, "proxy_host", None)

            if filter_network:
                proxy_mgr.set_filter_enabled(True)
            elif no_filter_network:
                proxy_mgr.set_filter_enabled(False)

            setup_cmd = SetupCommand(config, container_mgr, proxy_mgr)
            claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd, proxy_mgr)
            return claude_cmd.run(proxy_host)

    except ConfigExistsError as e:
        print(f"Error: {e}")
        return 1
    except ConfigNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ImageNameNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ContainerNotAvailableError as e:
        print(f"Error: {e}")
        return 1
    except ContainerBuildError as e:
        print(f"Error: {e}")
        return 1
    except ContainerRunError as e:
        print(f"Error: {e}")
        return 1
    except ProxyNotAvailableError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
