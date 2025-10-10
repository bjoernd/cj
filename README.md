# CJ (Claude Jailer)

CJ is a macOS application that runs Claude Code within an isolated container environment. It provides a sandboxed development environment with pre-installed development tools.

The main benefit is that CJ prevents malicious LLM agents to extract data from outside your project working directory. The project directory itself is intentionally read/writable. The container intentionally also has unrestricted network access.

## Features

- **Containerized Environment**: Runs Claude Code in an isolated Ubuntu 25.04 container
- **Pre-installed Tools**: Includes GCC, Clang, Python, Rust, Node.js, vim, neovim, zsh, and oh-my-zsh
- **Self-Bootstrapping**: No manual installation required - the `cj` script manages its own environment
- **Credential Persistence**: Claude Code credentials are automatically preserved across container runs

## Prerequisites

- macOS 26 (Tahoe) or later with the `container` command installed
- Python 3.9 or higher
- Node.js (for Claude Code)

## Installation

No installation required! Simply clone the repository and run the `cj` script from within your project directory:

```bash
git clone <repository-url>
cd <my-claude-project-directory>
<path-to-cj>/cj setup
```

On first run, `cj` will automatically:
1. Create a Python virtual environment in `.cj/venv`
2. Install all necessary dependencies to run cj later
3. Set up the project structure

## Usage

### Initial Setup

Before using CJ, you need to create the container image:

```bash
<path-to-cj>/cj setup
```

This command:
- Creates a `.cj` directory in your project
- Generates a Dockerfile with all development tools
- Builds a container image
- Stores the configuration for future use

To install additional Ubuntu packages during setup:

```bash
<path-to-cj>/cj setup --extra-packages "htop tmux wget"
```

Extra packages are stored in `.cj/extra-packages` and automatically included in future container rebuilds.

### Running Claude Code

Once setup is complete, simply run:

```bash
<path-to-cj>/cj
```

This launches Claude Code inside the container with:
- Your current directory mounted as `/workspace`
- Claude credentials persisted in `.cj/claude`
- Full access to all pre-installed development tools

### Updating the Container

To rebuild your container with the latest base image:

```bash
./cj update
```

This command:
- Pulls the latest Ubuntu 25.04 base image
- Regenerates the Dockerfile
- Rebuilds the container with the same name
- Preserves your Claude credentials
- Automatically includes previously specified extra packages

To add more packages during update:

```bash
./cj update --extra-packages "ncdu tree"
```

New packages are merged with existing ones and stored in `.cj/extra-packages`.

**Note**: User customizations to the Dockerfile will not be retained during updates. Use `--extra-packages` instead.

### Interactive Shell Access

To get a bash shell inside the container for debugging or manual operations:

```bash
./cj shell
```

This command:
- Launches an interactive bash shell in the container
- Provides the same environment and volume mounts as Claude Code
- Useful for debugging, testing, or running commands manually
- Exits with an error if the container image is not found (run `./cj setup` first)

## Commands

### `./cj`
Runs Claude Code in the container (default command).

### `./cj setup`
Creates project configuration and builds the container image.

### `./cj update`
Rebuilds the container image with the latest base image.

### `./cj shell`
Launches an interactive bash shell inside the container.

### `./cj --help`
Shows usage information and available commands.

## Project Structure

After running `./cj setup`, the following structure is created:

```
your-project/
├── .cj/
│   ├── venv/              # Python virtual environment (auto-managed)
│   ├── claude/            # Claude Code credentials (persisted)
│   ├── image-name         # Container image name
│   └── Dockerfile         # Container definition
└── (your project files)
```

## Container Environment

The container includes:

- **Base OS**: Ubuntu 25.04
- **Compilers**: GCC, Clang
- **Languages**: Python 3, Rust (stable), Node.js (LTS)
- **Editors**: vim, neovim
- **Shell**: zsh with oh-my-zsh
- **Tools**: curl, git
- **IDE**: Claude Code

## How It Works

### Self-Bootstrapping

The `cj` shell script automatically manages its own Python environment:

1. On first run, creates `.cj/venv` and installs dependencies
2. On subsequent runs, activates the existing environment
3. Executes the Python CLI module

### Credential Persistence

Claude Code credentials are persisted through volume mounts:

- `.cj/claude/` on host → `/root/.claude` in container
- First run creates credentials in the container
- Subsequent runs automatically have credentials available

### Container Isolation

Each project gets its own isolated container image with:

- Random image names to avoid conflicts
- Mounted workspace for file access
- Preserved credentials across runs

## Troubleshooting

### Container command not found

Ensure the macOS `container` command is installed and available in your PATH.

### Permission errors

The container runs as root inside, but files created are owned by your user on the host.

### Image rebuild needed

If you see "Container image not found", CJ will automatically rebuild it. You can also manually rebuild with `./cj update`.

### Virtual environment issues

If the virtual environment becomes corrupted, remove `.cj/venv` and run `./cj` again to recreate it.

## Development

### Running Tests

```bash
source .cj/venv/bin/activate
pytest tests/ -v
```

### Code Coverage

```bash
source .cj/venv/bin/activate
pytest tests/ --cov=cjlib --cov-report=term-missing
```

### Linting

```bash
source .cj/venv/bin/activate
flake8 cjlib/ tests/ --max-line-length=100
black cjlib/ tests/ --line-length=100
```

## Architecture

CJ consists of:

- **`cj`**: Self-bootstrapping shell script (entry point)
- **`cjlib/`**: Python package with all implementation logic
  - `cli.py`: Command-line interface and routing
  - `setup.py`: Setup mode implementation
  - `update.py`: Update mode implementation
  - `claude.py`: Claude mode implementation
  - `shell.py`: Shell mode implementation
  - `config.py`: Configuration management
  - `container.py`: Container operations wrapper
  - `namegen.py`: Random name generator

## License

[Your License Here]

## Contributing

Contributions are welcome! Please ensure:

- All tests pass: `pytest tests/`
- Code coverage remains >90%
- Code is formatted: `black cjlib/ tests/`
- Linting passes: `flake8 cjlib/ tests/`
