"""CLI argument parsing and command routing."""

import sys


def main():
    """Main entry point for CJ CLI."""
    print("CJ - Claude Jailer")
    print("Arguments:", sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
