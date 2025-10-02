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
from cjlib.setup import SetupCommand
from cjlib.update import UpdateCommand
from cjlib.claude import ClaudeCommand


def main():
    """Main entry point for CJ CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="CJ (Claude Jailer) - Run Claude Code in an isolated container"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup subcommand
    subparsers.add_parser("setup", help="Create project configuration and build container image")

    # Update subcommand
    subparsers.add_parser("update", help="Rebuild container image with latest base image")

    args = parser.parse_args()

    # Instantiate dependencies
    config = Config()
    container_mgr = ContainerManager()

    try:
        # Route to appropriate command
        if args.command == "setup":
            setup_cmd = SetupCommand(config, container_mgr)
            return setup_cmd.run()

        elif args.command == "update":
            update_cmd = UpdateCommand(config, container_mgr)
            return update_cmd.run()

        else:
            # Default: Claude mode (no subcommand)
            setup_cmd = SetupCommand(config, container_mgr)
            claude_cmd = ClaudeCommand(config, container_mgr, setup_cmd)
            return claude_cmd.run()

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
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
