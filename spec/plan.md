# CJ Implementation Plan

## Key Design Decisions

### Self-Bootstrapping Architecture
The `cj` command is a standalone shell script that requires no prior installation or setup. It automatically manages its own Python virtual environment:
- On first run, creates `.cj/venv` and installs dependencies
- On subsequent runs, activates the existing virtual environment
- Then executes the Python CLI module
- This ensures users can simply run `./cj` without manual environment setup

### Credential Persistence
Claude Code stores authentication credentials in `~/.claude/settings.json`. To persist these across container runs:
- Create a `.cj/claude` directory during setup
- Mount `.cj/claude` to `/root/.claude` in the container (read-write)
- On first run, Claude Code creates credentials in the container, which are stored in `.cj/claude/settings.json` on the host
- On subsequent runs, credentials are automatically available

This approach is simpler than copying files post-execution and ensures credentials persist naturally through volume mounts.

## Project Structure

```
cj/
├── cj                       # Self-bootstrapping shell script (main entry point)
├── cjlib/                   # Python package (renamed from 'cj' to avoid naming conflict)
│   ├── __init__.py
│   ├── __main__.py          # Entry point for `python -m cjlib`
│   ├── cli.py               # CLI argument parsing and command routing
│   ├── bootstrap.py         # Virtual environment bootstrapping logic
│   ├── setup.py             # Setup mode implementation
│   ├── update.py            # Update mode implementation
│   ├── claude.py            # Claude mode implementation
│   ├── container.py         # Container operations wrapper
│   ├── config.py            # Configuration management (.cj directory handling)
│   └── namegen.py           # Random name generator
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_bootstrap.py
│   ├── test_setup.py
│   ├── test_update.py
│   ├── test_claude.py
│   ├── test_container.py
│   ├── test_config.py
│   └── test_namegen.py
├── setup.py                 # Package setup for installation
├── pyproject.toml           # Modern Python packaging configuration
├── requirements.txt         # Runtime dependencies (empty - stdlib only)
├── requirements-dev.txt     # Development dependencies (pytest, etc.)
└── README.md
```

## Step 0: Self-Bootstrapping Shell Script ✓

**Objective:** Create the main `cj` shell script that handles virtual environment bootstrapping.

**Implementation Details:**

1. Create executable shell script `cj` in project root with the following behavior:
   - Detect script directory using `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
   - Check if `.cj/venv` exists
   - If not exists:
     - Print message: "First run detected, setting up environment..."
     - Create `.cj` directory if it doesn't exist
     - Create virtual environment: `python3 -m venv .cj/venv`
     - Activate virtual environment
     - Install the cj package in editable mode from `$SCRIPT_DIR`
     - Print message: "Environment setup complete"
   - If exists:
     - Activate virtual environment
   - Execute Python CLI: `python -m cjlib "$@"`
   - Pass through exit code

2. The script should handle errors gracefully:
   - Check if `python3` is available
   - Check if `venv` module is available
   - Provide helpful error messages

**File:** `cj` (shell script, no extension)

**Testing:**
- Manual test: Run `./cj --help` on fresh checkout
- Verify virtual environment is created in `.cj/venv`
- Verify subsequent runs reuse the environment
- Verify arguments are passed through correctly

**Success Criteria:**
- First run creates virtual environment automatically
- Subsequent runs activate existing environment
- Arguments are passed through to Python CLI
- Script is executable (`chmod +x cj`)

## Step 1: Project Scaffolding and Development Environment ✓

**Objective:** Set up the Python project structure with proper packaging configuration and development tools.

**Implementation Details:**

1. Create the directory structure as shown above
2. Initialize `pyproject.toml` with:
   - Project metadata (name: "cj", version: "0.1.0")
   - Build system using setuptools
   - Entry point: `cj = cjlib.cli:main`
   - Python version requirement: >= 3.9
   - No external dependencies (use only stdlib)
3. Create `setup.py` for backwards compatibility
4. Create `requirements.txt` (empty file - all stdlib)
5. Create `requirements-dev.txt` with:
   - pytest >= 7.0
   - pytest-cov (for code coverage)
6. Create basic `__init__.py` files in `cjlib/` and `tests/`
7. Create a `.gitignore` for Python projects (ignore `__pycache__`, `.pytest_cache`, `*.pyc`, `.cj/`, etc.)

**Testing:**
- Install in editable mode: `pip install -e .`
- Verify package structure: `python -c "import cjlib"`
- Run pytest (should find 0 tests): `pytest tests/`

**Success Criteria:**
- `pip install -e .` succeeds
- Package imports successfully
- pytest runs without errors

## Step 2: Configuration Management Module ✓

**Objective:** Implement the configuration management system for handling `.cj` directory and its contents.

**File:** `cjlib/config.py`

**Implementation Details:**

1. Define constants:
   - `CONFIG_DIR = ".cj"`
   - `IMAGE_NAME_FILE = "image-name"`
   - `DOCKERFILE_NAME = "Dockerfile"`
   - `CLAUDE_DIR = "claude"`
   - `VENV_DIR = "venv"` (note: managed by shell script, but Config should be aware)
2. Implement `Config` class with methods:
   - `__init__(self, base_dir: str = ".")`: Store base directory path
   - `get_config_dir(self) -> str`: Return full path to `.cj` directory
   - `exists(self) -> bool`: Check if `.cj` directory exists
   - `create_config_dir(self) -> None`: Create `.cj` directory (raise if exists)
   - `get_image_name_path(self) -> str`: Return path to `image-name` file
   - `read_image_name(self) -> str`: Read and return image name (raise if not found)
   - `write_image_name(self, name: str) -> None`: Write image name to file
   - `get_dockerfile_path(self) -> str`: Return path to Dockerfile
   - `get_claude_dir(self) -> str`: Return path to `.cj/claude` directory
   - `ensure_claude_dir(self) -> None`: Create `.cj/claude` directory if it doesn't exist
   - `get_venv_dir(self) -> str`: Return path to `.cj/venv` directory
   - `cleanup(self) -> None`: Remove `.cj` directory and contents (including venv)
3. Add proper error handling with custom exceptions:
   - `ConfigExistsError`: Raised when `.cj` already exists
   - `ConfigNotFoundError`: Raised when `.cj` doesn't exist
   - `ImageNameNotFoundError`: Raised when image-name file doesn't exist

**File:** `tests/test_config.py`

**Testing:**
1. Test `Config` initialization with different base directories
2. Test `exists()` returns False when no config, True when exists
3. Test `create_config_dir()`:
   - Successfully creates directory
   - Raises `ConfigExistsError` when already exists
4. Test `write_image_name()` and `read_image_name()`:
   - Write then read returns same value
   - Read without write raises `ImageNameNotFoundError`
5. Test `get_dockerfile_path()` returns correct path
6. Test `get_claude_dir()` returns correct path
7. Test `ensure_claude_dir()`:
   - Creates directory if it doesn't exist
   - Doesn't error if directory already exists
8. Test `cleanup()` removes entire `.cj` directory
9. Use `tmp_path` pytest fixture for isolated file system testing

**Success Criteria:**
- All tests pass: `pytest tests/test_config.py -v`
- Code coverage > 95%: `pytest tests/test_config.py --cov=cjlib.config`

## Step 3: Random Name Generator ✓

**Objective:** Implement random name generator for container images.

**File:** `cjlib/namegen.py`

**Implementation Details:**

1. Define two word lists (10-20 words each):
   - Adjectives: `["happy", "clever", "brave", "gentle", "swift", "bright", "calm", "bold", ...]`
   - Nouns: `["turtle", "falcon", "river", "mountain", "forest", "ocean", "wind", "star", ...]`
2. Implement `generate_name() -> str`:
   - Use `random.choice()` to select one adjective and one noun
   - Return formatted as `"cj-{adjective}-{noun}"`
   - Use `random.seed()` capability for testing but don't set seed by default
3. Implement `is_valid_name(name: str) -> bool`:
   - Check if name matches pattern `cj-[a-z]+-[a-z]+`
   - Return True/False

**File:** `tests/test_namegen.py`

**Testing:**
1. Test `generate_name()`:
   - Returns string in correct format
   - Multiple calls return different names (probabilistic test)
   - Test with fixed seed for reproducibility
2. Test `is_valid_name()`:
   - Valid names return True
   - Invalid formats return False (test: "cj-only-one", "no-prefix", "CJ-upper-case", "cj-with-numbers-123")

**Success Criteria:**
- All tests pass: `pytest tests/test_namegen.py -v`
- Code coverage 100%: `pytest tests/test_namegen.py --cov=cjlib.namegen`

## Step 4: Container Operations Wrapper ✓

**Objective:** Create abstraction layer for macOS `container` command operations.

**File:** `cjlib/container.py`

**Implementation Details:**

1. Import `subprocess`, `shutil`, `os`
2. Implement helper function `_run_command(args: list[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess`:
   - Execute command using `subprocess.run()`
   - Handle errors appropriately
   - Return CompletedProcess object
3. Implement `ContainerManager` class with methods:
   - `check_container_available(self) -> bool`: Check if `container` command exists using `shutil.which()`
   - `build_image(self, dockerfile_path: str, tag: str, context_dir: str) -> None`:
     - Run `container build -t {tag} -f {dockerfile_path} {context_dir}`
     - Raise `ContainerBuildError` on failure
   - `image_exists(self, tag: str) -> bool`:
     - Run `container image list` and check if tag is in output
     - Return True/False
   - `run_interactive(self, image: str, working_dir: str, volume_mounts: list[str], command: list[str]) -> int`:
     - Run `container run -it --rm -v {mount1} -v {mount2} ... -w {working_dir} {image} {command}`
     - Support multiple volume mounts
     - Return exit code
   - `remove_image(self, tag: str) -> None`:
     - Run `container image delete {tag}`
     - Ignore errors if image doesn't exist
4. Define custom exceptions:
   - `ContainerNotAvailableError`: container command not found
   - `ContainerBuildError`: Build failed
   - `ContainerRunError`: Run failed

**File:** `tests/test_container.py`

**Testing:**
1. Mock `subprocess.run()` and `shutil.which()` using `unittest.mock`
2. Test `check_container_available()`:
   - Returns True when `container` command exists
   - Returns False when command not found
3. Test `build_image()`:
   - Calls correct subprocess command
   - Raises `ContainerBuildError` on failure
4. Test `image_exists()`:
   - Returns True when image in list output
   - Returns False when image not in list output
5. Test `run_interactive()`:
   - Calls correct subprocess command with all parameters
   - Returns correct exit code
6. Test `remove_image()`:
   - Calls correct subprocess command
   - Doesn't raise error when image doesn't exist

**Success Criteria:**
- All tests pass: `pytest tests/test_container.py -v`
- Code coverage > 90%: `pytest tests/test_container.py --cov=cjlib.container`

## Step 5: Setup Mode Implementation ✓

**Objective:** Implement `cj setup` command that creates project configuration and builds container image.

**File:** `cjlib/setup.py`

**Implementation Details:**

1. Define Dockerfile template as module constant:
```python
DOCKERFILE_TEMPLATE = """FROM ubuntu:25.04

# Update package lists and install development tools
RUN apt-get update && apt-get install -y \\
    gcc g++ \\
    clang \\
    python3 python3-dev python3-pip python3-venv \\
    python3-pytest python3-black \\
    vim neovim \\
    zsh \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Install Rust via rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile default
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustc --version && cargo --version

# Install Node.js (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \\
    && apt-get install -y nodejs \\
    && rm -rf /var/lib/apt/lists/*

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Set zsh as default shell
RUN chsh -s $(which zsh)
ENV SHELL=/usr/bin/zsh

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Set working directory
WORKDIR /workspace

CMD ["/usr/bin/zsh"]
"""
```

2. Implement `SetupCommand` class:
   - `__init__(self, config: Config, container_mgr: ContainerManager)`: Store dependencies
   - `_generate_dockerfile(self, path: str) -> None`: Write DOCKERFILE_TEMPLATE to path
   - `_cleanup_on_failure(self) -> None`: Remove .cj directory on build failure
   - `run(self) -> int`: Main execution method
     - Check if config already exists (raise error if yes)
     - Check if container command available (raise error if not)
     - Create config directory
     - Generate random image name
     - Write Dockerfile
     - Build container image (cleanup on failure)
     - Write image name to config
     - Print success message
     - Return 0 on success, 1 on failure

**File:** `tests/test_setup.py`

**Testing:**
1. Use mocks for `Config` and `ContainerManager`
2. Test successful setup flow:
   - Config directory created
   - Dockerfile written
   - Image built with correct tag
   - Image name saved
   - Success message printed
3. Test failure when `.cj` already exists:
   - Appropriate error message
   - Returns exit code 1
4. Test failure when container not available:
   - Appropriate error message
   - Returns exit code 1
5. Test cleanup on build failure:
   - `.cj` directory removed
   - Dockerfile preserved for inspection (actually, spec says "clean up temporary build artifacts but preserve Dockerfile")
   - Returns exit code 1
6. Test Dockerfile content:
   - Verify template includes all required tools
   - Verify oh-my-zsh installation
   - Verify Claude Code installation

**Success Criteria:**
- All tests pass: `pytest tests/test_setup.py -v`
- Code coverage > 90%: `pytest tests/test_setup.py --cov=cjlib.setup`

## Step 6: Update Mode Implementation

**Objective:** Implement `cj update` command that rebuilds container image with latest base image.

**File:** `cjlib/update.py`

**Implementation Details:**

1. Implement `UpdateCommand` class:
   - `__init__(self, config: Config, container_mgr: ContainerManager)`: Store dependencies
   - `run(self) -> int`: Main execution method
     - Check if config exists (raise error if not)
     - Read existing image name from config
     - Read Dockerfile from config directory
     - Regenerate Dockerfile with original template (spec says "User customizations to the Dockerfile will not be retained")
     - Pull latest base image: `container pull ubuntu:25.04`
     - Rebuild container image with same tag
     - Print success message
     - Return 0 on success, 1 on failure

2. Add method to pull base image:
   - `_pull_base_image(self) -> None`: Run `container pull ubuntu:25.04`

**File:** `tests/test_update.py`

**Testing:**
1. Use mocks for `Config` and `ContainerManager`
2. Test successful update flow:
   - Config exists
   - Image name read correctly
   - Base image pulled
   - Image rebuilt with same tag
   - Success message printed
3. Test failure when no `.cj` directory:
   - Appropriate error message
   - Returns exit code 1
4. Test that Dockerfile is regenerated (not reused):
   - Verify new Dockerfile written
   - User customizations would be lost

**Success Criteria:**
- All tests pass: `pytest tests/test_update.py -v`
- Code coverage > 90%: `pytest tests/test_update.py --cov=cjlib.update`

## Step 7: Claude Mode Implementation

**Objective:** Implement default `cj` command that runs Claude Code in container.

**File:** `cjlib/claude.py`

**Implementation Details:**

1. Define constants:
   - `CONTAINER_CLAUDE_DIR = "/root/.claude"`
   - `CONTAINER_WORKSPACE = "/workspace"`

2. Implement `ClaudeCommand` class:
   - `__init__(self, config: Config, container_mgr: ContainerManager, setup_cmd: SetupCommand)`: Store dependencies
   - `run(self) -> int`: Main execution method
     - Check if config exists
       - If not, print error asking user to run `cj setup`
       - Return 1
     - Read image name from config
     - Check if image exists
       - If not, print message about rebuilding
       - Call `setup_cmd.run()` to rebuild (reusing setup logic)
       - Re-read image name
     - Ensure `.cj/claude` directory exists (for credential persistence)
     - Prepare volume mounts:
       - Mount current directory as `/workspace`
       - Mount `.cj/claude` as `/root/.claude`
     - Run container interactively:
       - Mount volumes as prepared above
       - Set working directory to `/workspace`
       - Run `claude` command
     - Return container exit code

3. Helper methods:
   - `_get_volume_mounts(self) -> list[str]`: Return list of volume mount strings
     - `{cwd}:/workspace`
     - `{config_dir}/claude:/root/.claude`
   - `_rebuild_image(self) -> None`: Use SetupCommand to rebuild

**File:** `tests/test_claude.py`

**Testing:**
1. Use mocks for `Config`, `ContainerManager`, and `SetupCommand`
2. Test successful Claude launch:
   - Config exists
   - Image exists
   - `.cj/claude` directory created if needed
   - Container runs with correct parameters
   - Two volume mounts: workspace + claude directory
   - Working directory set to `/workspace`
   - Command is `["claude"]`
   - Returns container exit code
3. Test no config scenario:
   - Error message printed
   - Returns exit code 1
   - Container not launched
4. Test image missing scenario:
   - Message about rebuilding printed
   - Setup command called
   - Container launched after rebuild
5. Test volume mount construction:
   - `_get_volume_mounts()` returns correct list with both mounts
   - Workspace mount: `{cwd}:/workspace`
   - Claude directory mount: `{cwd}/.cj/claude:/root/.claude`
6. Test `.cj/claude` directory creation:
   - Verify `ensure_claude_dir()` called before running container
   - Directory created if it doesn't exist

**Success Criteria:**
- All tests pass: `pytest tests/test_claude.py -v`
- Code coverage > 90%: `pytest tests/test_claude.py --cov=cjlib.claude`

## Step 8: CLI and Command Routing

**Objective:** Implement command-line interface and route commands to appropriate handlers.

**File:** `cjlib/cli.py`

**Implementation Details:**

1. Import `argparse`, `sys`, and command classes
2. Implement `main()` function:
   - Create argument parser with description
   - Add subparsers for commands:
     - `setup`: Setup subcommand
     - `update`: Update subcommand
     - (no subcommand): Claude mode (default)
   - Parse arguments
   - Instantiate dependencies (Config, ContainerManager)
   - Route to appropriate command based on subcommand:
     - `setup`: Create and run SetupCommand
     - `update`: Create and run UpdateCommand
     - None: Create and run ClaudeCommand
   - Handle exceptions and print user-friendly error messages
   - Return exit code from command

3. Error handling:
   - Catch all custom exceptions
   - Print clear error messages
   - Return appropriate exit codes

**File:** `cjlib/__main__.py`

**Implementation Details:**
```python
from cjlib.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

**File:** `tests/test_cli.py`

**Testing:**
1. Mock command classes and their run methods
2. Test `setup` subcommand routing:
   - Verify SetupCommand instantiated and run
3. Test `update` subcommand routing:
   - Verify UpdateCommand instantiated and run
4. Test default (no args) routing:
   - Verify ClaudeCommand instantiated and run
5. Test exit code propagation:
   - Command return codes passed through
6. Test error handling:
   - Exceptions caught and converted to error messages
   - Appropriate exit codes returned

**Success Criteria:**
- All tests pass: `pytest tests/test_cli.py -v`
- Code coverage > 85%: `pytest tests/test_cli.py --cov=cjlib.cli`
- Can run `cj --help` and see usage information
- Can run `python -m cjlib --help` and see usage information

## Step 9: Installation and Integration Testing

**Objective:** Ensure the package can be installed and all commands work together.

**Implementation Details:**

1. Create `README.md` with:
   - Project description
   - Installation instructions
   - Usage examples for all three modes
   - Requirements (macOS with container tool)

2. Verify `pyproject.toml` entry points:
   - Console script: `cj = cjlib.cli:main`

3. Create integration test script `tests/test_integration.py`:
   - These are manual tests (marked with `pytest.mark.skip` by default)
   - Test full setup flow in temporary directory
   - Test update flow
   - Test Claude mode (if possible to mock/test)

**Testing:**
1. Clean install in fresh virtual environment:
   ```bash
   python -m venv test_venv
   source test_venv/bin/activate
   pip install -e .
   ```
2. Verify `cj` command available: `which cj`
3. Run all unit tests: `pytest tests/ -v`
4. Run with coverage: `pytest tests/ --cov=cjlib --cov-report=html`
5. Verify coverage > 90% overall

**Success Criteria:**
- Package installs without errors
- `cj` command available in PATH
- All unit tests pass
- Overall code coverage > 90%
- Manual smoke test of `cj setup` succeeds (creates `.cj`, Dockerfile, builds image)

## Step 10: Documentation and Finalization

**Objective:** Complete documentation and prepare for release.

**Implementation Details:**

1. Update `README.md` with:
   - Clear description of what CJ does
   - Prerequisites section (macOS, container tool, Node.js)
   - Installation section
   - Usage section with examples
   - Troubleshooting section
   - Development section (how to contribute, run tests)

2. Add docstrings to all modules, classes, and public functions:
   - Use Google-style or NumPy-style docstrings
   - Include parameter descriptions
   - Include return value descriptions
   - Include exception documentation

3. Create `CLAUDE.md` in project root:
   - Document project structure
   - Document testing strategy
   - Document design decisions
   - Note dependencies on macOS container tool

4. Add inline comments for complex logic

**Testing:**
- Run full test suite: `pytest tests/ -v --cov=cjlib`
- Verify all tests pass
- Verify coverage > 90%
- Manual testing of all three modes on macOS with container tool

**Success Criteria:**
- All tests pass
- Code coverage > 90%
- Documentation complete
- README is clear and accurate
- Code is well-commented

## Testing Strategy Summary

Each step includes:
1. Unit tests for all new code
2. Test execution after implementation
3. Coverage verification (>90% per module)
4. All tests must pass before moving to next step

Testing approach:
- Use `pytest` as test runner
- Use `unittest.mock` for mocking external dependencies
- Use `tmp_path` fixture for file system tests
- Use parameterized tests where appropriate
- Test both success and failure paths
- Test edge cases and error conditions

## Dependencies

Runtime dependencies (all Python stdlib):
- `argparse` (CLI)
- `subprocess` (container commands)
- `pathlib` or `os.path` (file operations)
- `random` (name generation)
- `json` (if needed for config)

Development dependencies:
- `pytest >= 7.0`
- `pytest-cov` (coverage)

## Notes

- The implementation uses only Python standard library for runtime
- Requires macOS with `container` command installed
- Container images are specific to the project directory
- Each project gets its own isolated container image
- Image names are randomly generated to avoid conflicts
