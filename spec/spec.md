## Overview

This is CJ, the Claude Jailer. CJ runs Claude Code within a container image. The container is running in a lightweight virtual machine to achieve isolation from the rest of the host system.

## Details

This is a MacOS application and we will be using MacOS's `container` toolilng that allows running Linux containers on MacOS. You can find documentation on the `container` tool here:
- Overview: https://github.com/apple/container/blob/main/docs/technical-overview.md
- How-to: https://github.com/apple/container/blob/main/docs/how-to.md
- Command Reference: https://github.com/apple/container/blob/main/docs/command-reference.md

The command line utility will be called `cj` and we will write it in Python.

## Self-Bootstrapping Behavior

The `cj` script is designed to run without any prior setup or installation. It automatically manages its own virtual environment:

1. When executed, `cj` checks if a virtual environment exists in `.cj/venv`
2. If no virtual environment exists:
   - Automatically creates one using `python3 -m venv .cj/venv`
   - Installs required dependencies into the virtual environment
3. If a virtual environment exists, automatically activates it
4. Then proceeds with the requested command (setup, update, or claude mode)

This design ensures users can simply run `cj` without needing to manually create virtual environments or install dependencies. The virtual environment is stored in `.cj/venv` to keep it isolated per project.

## CJ Modes

CJ will allow modal execution.

### Setup mode

`cj setup` will create a new cj project in the current directory. We will create a .cj subdirectory to keep our configuration and files. We will create a Dockerfile in the .cj subdirectory that builds based on the Ubuntu 25.04 docker image. In this container we will install common development tools:
- GCC and G++ compilers
- Clang and Clang++ compilers
- Latest Python version available in the Ubuntu 25.04 image, including pip and development packages (python3-dev, python3-pip, python3-venv, pytest, black) to allow users to create virtual environments
- Rust via rustup with the default toolchain using Rust 2024 edition

We will also install vim, neovim and zsh in the container image.

We will install [oh-my-zsh](https://ohmyz.sh) and make zsh the default shell in the container image.

We will install Claude Code inside the container via npm as documented at https://docs.claude.com/en/docs/claude-code/overview. Claude Code will handle credential management on first use.

We will build a container image from that generated Dockerfile (container build...). We will label the container image with a randomly generated name using the format `cj-<word1>-<word2>` (e.g., cj-happy-turtle). We will store this image name in .cj/image-name for later reference.

If there is already a .cj directory with an image-name, we will abort and inform the user about this situation.

If the container build fails, we will clean up any temporary build artifacts but preserve the generated Dockerfile for inspection.

On successful execution we will print a success message and instruct the user to next run "cj".

### Update Mode

`cj update` will create a new version of our container image. This includes pulling the latest version of the base image and rebuilding the container image with "container build....". The update will only affect subsequent container launches. User customizations to the Dockerfile will not be retained.

### Claude mode

When run without command line arguments, `cj` will read the local .cj directory to identify the container that was created for the current project. cj will launch this container in interactive mode (container -it run ...). cj will share the entire current project directory with the running container in read-write mode and use the directory as the working directory in the container. cj will invoke `claude` inside the container, so that the user can start interacting with Claude Code. The container will remain running for the duration of the Claude Code session and will be terminated when the user exits Claude Code.

If no .cj directory is present, cj will provide an error message asking the user to run `cj setup` first.

If the container image specified in .cj is not available, cj will rebuild the container image the same way as if we ran `cj setup`. This will allow updating to latest versions of the base container.

#### Credential Persistence

Claude Code stores its authentication credentials in `~/.claude/settings.json`. To persist credentials across container runs:

1. Create a `.cj/claude` directory during setup (if it doesn't exist)
2. Always mount `.cj/claude` to `/root/.claude` in the container (read-write)
3. On first run, Claude Code will create `/root/.claude/settings.json` in the container, which is actually stored in `.cj/claude/settings.json` on the host
4. On subsequent runs, the credentials are automatically available because the same directory is mounted

This ensures users only need to authenticate once per project, and credentials are stored locally in the project's `.cj/claude` directory.
