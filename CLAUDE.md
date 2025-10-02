# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CJ (Claude Jailer) is a macOS application that runs Claude Code within an isolated container environment. It uses macOS's native `container` tool to provide a sandboxed development environment with pre-installed development tools.

## Architecture

### Self-Bootstrapping Design

The `cj` command is a bash script that manages its own Python virtual environment:
- First run: Creates `.cj/venv`, installs dependencies, and sets up the Python package
- Subsequent runs: Activates existing venv and executes `python -m cjlib`
- No manual installation or setup required by users

### Package Structure

- **`cj`** (bash script): Entry point that handles venv bootstrapping
- **`cjlib/`**: Python package containing all implementation logic
  - Python package is named `cjlib` (not `cj`) to avoid filesystem naming conflicts with the bash script
  - Modules use only Python stdlib (no external dependencies at runtime)

### Key Components

- **`config.py`**: Manages `.cj` directory structure, image names, Dockerfile paths
  - Custom exceptions: `ConfigExistsError`, `ConfigNotFoundError`, `ImageNameNotFoundError`
  - Handles credential persistence in `.cj/claude/`

- **`container.py`** (planned): Wrapper for macOS `container` command operations
- **`namegen.py`** (planned): Generates random names like `cj-happy-turtle` for container images
- **`setup.py`** (planned): Implements `cj setup` - creates Dockerfile and builds container
- **`update.py`** (planned): Implements `cj update` - rebuilds container with latest base image
- **`claude.py`** (planned): Implements default `cj` command - runs Claude Code in container
- **`cli.py`**: Currently minimal, will route commands to appropriate handlers

### Container Integration

CJ targets macOS's `container` tool (not Docker). Key differences:
- Command: `container` instead of `docker`
- Uses Ubuntu 25.04 as base image
- Installs: GCC, Clang, Python, Rust, Node.js, vim, neovim, zsh, oh-my-zsh, Claude Code

### Credential Persistence Strategy

Claude Code credentials persist across container runs via volume mounts:
- `.cj/claude/` on host → `/root/.claude` in container
- First run creates credentials in container (stored on host)
- Subsequent runs automatically have credentials available

## Development Commands

### Running Tests

```bash
# Activate virtual environment (if not using ./cj script)
source .cj/venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest tests/test_config.py --cov=cjlib.config --cov-report=term-missing

# Coverage target: >95% per module, >90% overall
```

### Linting

**IMPORTANT**: Before committing changes to git, always run linting and fix all issues:

```bash
source .cj/venv/bin/activate

# Install linting tools (if not already installed)
pip install flake8 black

# Run flake8 linting
flake8 cjlib/ tests/ --max-line-length=100 --statistics

# Run black formatter
black cjlib/ tests/ --line-length=100

# Verify linting passes before committing
```

### Development Setup

```bash
# First time: Run cj script to bootstrap environment
./cj --help

# Install development dependencies manually (optional, cj script does this)
source .cj/venv/bin/activate
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

## Implementation Progress

Tracked in `spec/plan.md` with checkmarks (✓):
- ✓ Step 0: Self-Bootstrapping Shell Script
- ✓ Step 1: Project Scaffolding and Development Environment
- ✓ Step 2: Configuration Management Module
- Step 3: Random Name Generator (next)
- Step 4: Container Operations Wrapper
- Step 5: Setup Mode Implementation
- Step 6: Update Mode Implementation
- Step 7: Claude Mode Implementation
- Step 8: CLI and Command Routing
- Step 9: Integration Testing
- Step 10: Documentation

## Testing Requirements

Per implementation plan:
- Use `tmp_path` fixture for filesystem tests
- Test both success and error paths
- Include edge cases and error conditions
- Target >95% coverage per module
- Mock external dependencies (subprocess, container commands)

## Git Workflow

1. Implement feature/step
2. Run linting: `flake8` and `black`
3. Fix all linting issues
4. Run tests and verify they pass
5. Mark step as completed in `spec/plan.md` (add ✓)
6. Commit with descriptive message including:
   - What was implemented
   - Test results
   - Coverage metrics
   - Standard footer with Claude Code attribution