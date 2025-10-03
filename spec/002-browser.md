# Browser Redirection Implementation Plan

## Overview

Implement browser URL redirection from container to host using SSH reverse tunnel. When Claude Code (or any process) inside the container attempts to open a URL, it gets opened in the host's default browser instead.

## Architecture

```
Container Process → /usr/local/bin/open wrapper → localhost:9999 (forwarded port)
                                                         ↓
Host listening on localhost:9999 ← SSH reverse tunnel ← SSH server in container
         ↓
Host's `open` command → macOS default browser
```

## Implementation Steps

### Step 1: Add SSH Server to Container Image

**File: `cjlib/config.py`**
- No changes needed

**File: Container Dockerfile template**
- Install `openssh-server` package
- Configure SSH to allow root login with key auth only
- Create SSH host keys during build
- Set up SSH daemon to start automatically
- Expose SSH port (default 22 or custom port like 2222)

**Dockerfile additions:**
```dockerfile
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh
```

### Step 2: SSH Key Management

**File: `cjlib/container.py`**

Add new functions:
- `setup_ssh_keys()`: Generate SSH key pair for host if not exists
  - Store in `.cj/ssh/id_rsa` and `.cj/ssh/id_rsa.pub`
  - Set proper permissions (600 for private key)
  - Use `ssh-keygen -t rsa -b 4096 -f .cj/ssh/id_rsa -N ''`

**File: `cjlib/config.py`**

Add configuration:
- `SSH_DIR`: Path to `.cj/ssh/` directory
- `SSH_PRIVATE_KEY`: Path to host's private key
- `SSH_PUBLIC_KEY`: Path to host's public key
- `BROWSER_BRIDGE_PORT`: Port for reverse tunnel (default 9999)

**SSH Key Injection Strategy:**

Keys are injected at container startup (not during build):

1. Mount `.cj/ssh/` → `/tmp/host-ssh/` in container
2. Add init script to Dockerfile that runs at container start:
   ```bash
   #!/bin/bash
   # /usr/local/bin/init-ssh.sh
   mkdir -p /root/.ssh
   if [ -f /tmp/host-ssh/id_rsa.pub ]; then
     cat /tmp/host-ssh/id_rsa.pub > /root/.ssh/authorized_keys
     chmod 600 /root/.ssh/authorized_keys
     chmod 700 /root/.ssh
   fi
   exec /usr/sbin/sshd -D
   ```
3. Container CMD runs this init script instead of direct sshd

**Benefits of this approach:**
- Each CJ installation has unique SSH keys
- Keys not baked into container image
- Keys can be regenerated without rebuilding container
- No modification of host SSH configuration

### Step 3: Browser Wrapper Script

**File: `cjlib/templates/open-wrapper.sh`** (new file)

Create wrapper script to be installed in container at `/usr/local/bin/open`:

```bash
#!/bin/bash
# Browser URL wrapper - forwards URLs to host via reverse SSH tunnel

PORT=9999
URL="$*"

# Send URL to host via forwarded port
echo "$URL" | nc -w 1 localhost $PORT 2>/dev/null

# Exit successfully even if nc fails (host might not be listening)
exit 0
```

**Dockerfile addition:**
```dockerfile
COPY open-wrapper.sh /usr/local/bin/open
RUN chmod +x /usr/local/bin/open
ENV BROWSER=/usr/local/bin/open
```

### Step 4: Host-Side URL Listener

**File: `cjlib/browser_bridge.py`** (new module)

Implement host-side listener that:
- Listens on localhost:9999 for incoming URLs
- Translates `file://` URLs from container paths to host paths
- Calls macOS `open` command for each URL received
- Runs as background thread/process

```python
import socket
import subprocess
import threading
import logging

class BrowserBridge:
    def __init__(self, port=9999, path_mappings=None):
        """
        Initialize browser bridge.

        Args:
            port: Port to listen on (default 9999)
            path_mappings: List of (container_path, host_path) tuples for file:// URL translation
        """
        self.port = port
        self.path_mappings = path_mappings or []
        self.running = False

    def start(self):
        """Start listening for URLs in background thread"""

    def stop(self):
        """Stop the listener"""

    def _listen(self):
        """Main listener loop - receives URLs and opens them"""
        # Create socket, bind to localhost:port
        # Accept connections, read URL
        # Translate URL if needed
        # Call subprocess.run(['open', translated_url])

    def _translate_url(self, url):
        """
        Translate file:// URLs from container paths to host paths.

        Args:
            url: URL to translate (may be file://, http://, https://, etc.)

        Returns:
            Translated URL (or original if no translation needed)
        """
        if not url.startswith('file://'):
            return url  # HTTP/HTTPS pass through unchanged

        # Extract path from file:// URL
        container_path = url[7:]  # Remove 'file://' prefix

        # Try each path mapping in order
        for container_prefix, host_prefix in self.path_mappings:
            if container_path.startswith(container_prefix):
                # Replace container prefix with host prefix
                host_path = container_path.replace(container_prefix, host_prefix, 1)
                return f'file://{host_path}'

        # No mapping found - log warning and return original
        # (will likely fail to open, but better than silent failure)
        logging.warning(f"No path mapping found for container path: {container_path}")
        return url
```

**Path Mapping Examples:**

```python
# Volume mounts in container:
# /Users/bjoernd/src/cj → /root/project (working directory)
# /Users/bjoernd/src/cj/.cj/claude → /root/.claude (credentials)

path_mappings = [
    ('/root/project', '/Users/bjoernd/src/cj'),
    ('/root/.claude', '/Users/bjoernd/src/cj/.cj/claude'),
]

# Translation examples:
# file:///root/project/output.html → file:///Users/bjoernd/src/cj/output.html ✓
# file:///root/.claude/logs/debug.html → file:///Users/bjoernd/src/cj/.cj/claude/logs/debug.html ✓
# https://example.com → https://example.com (unchanged) ✓
# file:///tmp/report.html → file:///tmp/report.html (no mapping, warning logged)
```

### Step 5: SSH Reverse Tunnel Setup

**File: `cjlib/container.py`**

Modify `ContainerManager.run_interactive()`:

Add new method:
- `setup_reverse_tunnel()`: Establish SSH connection with reverse tunnel
  - Returns subprocess.Popen object for SSH connection
  - Command: `ssh -R 9999:localhost:9999 -i .cj/ssh/id_rsa root@container_ip -N`
  - Need to determine container's IP after it starts

**Challenge**: Getting container's IP address
- Option A: Container tool may expose IP via inspection command
- Option B: Use container's hostname/DNS if supported
- Option C: Use port forwarding instead (forward container's SSH port to host)

**Revised approach using port forwarding:**
- Start container with port mapping: `-p 2222:22` (container SSH → host port 2222)
- Host connects: `ssh -R 9999:localhost:9999 -p 2222 -i .cj/ssh/id_rsa root@localhost -N`
- Simpler: no IP discovery needed

### Step 6: Orchestration in Main Flow

**File: `cjlib/claude.py`** (or wherever container launch happens)

Update flow:
1. Start BrowserBridge listener on host
2. Start container with SSH port forwarding
3. Wait for SSH daemon in container to be ready
4. Establish reverse SSH tunnel
5. Launch Claude Code in container
6. On exit: cleanup tunnel and stop listener

**Pseudocode:**
```python
# Define volume mounts (used for both container and path translation)
volume_mounts = [
    ('/Users/bjoernd/src/cj', '/root/project'),
    ('/Users/bjoernd/src/cj/.cj/claude', '/root/.claude'),
    ('/Users/bjoernd/src/cj/.cj/ssh', '/tmp/host-ssh'),
]

# Create path mappings for file:// URL translation (container→host)
path_mappings = [
    (container_path, host_path)
    for host_path, container_path in volume_mounts
    if not container_path.startswith('/tmp')  # Skip temp mounts
]

# Start browser bridge with path mappings
bridge = BrowserBridge(port=9999, path_mappings=path_mappings)
bridge.start()

container_mgr.run_interactive(
    image_name=image,
    volume_mounts=volume_mounts,
    port_forwards=[("2222", "22")]  # New parameter
)

# In separate thread/process:
tunnel = container_mgr.setup_reverse_tunnel(
    ssh_port=2222,
    forward_port=9999
)

# Wait for container to exit
# ...

tunnel.terminate()
bridge.stop()
```

### Step 7: Error Handling

**File: `cjlib/container.py`**

Add custom exceptions:
- `SSHKeyError`: SSH key generation/setup failed
- `SSHTunnelError`: Reverse tunnel establishment failed
- `SSHConnectionError`: Cannot connect to container's SSH

Handle cases:
- SSH daemon not ready in container (retry with backoff)
- Tunnel dies during session (attempt reconnect)
- Port 9999 already in use (try alternative port)
- Container has no SSH server (graceful degradation)

### Step 8: Testing

**File: `tests/test_browser_bridge.py`** (new file)

Test cases:
- `test_browser_bridge_starts_and_stops()`: Listener lifecycle
- `test_browser_bridge_receives_url()`: Send URL via socket, verify `open` called
- `test_browser_bridge_handles_invalid_url()`: Error handling
- `test_browser_bridge_port_already_in_use()`: Port conflict handling
- `test_translate_file_url()`: Test file:// URL path translation
- `test_translate_http_url()`: Test HTTP/HTTPS URLs pass through unchanged
- `test_translate_url_no_mapping()`: Test unmapped paths log warning
- `test_path_mappings_order()`: Test that first matching mapping wins

**File: `tests/test_container.py`**

Add test cases:
- `test_setup_ssh_keys()`: Key generation
- `test_inject_ssh_key()`: Key injection into container
- `test_setup_reverse_tunnel()`: Tunnel establishment (mocked)
- `test_run_with_port_forwarding()`: Container launch with port mapping

**File: `tests/test_integration_browser.py`** (new file)

Integration test:
- Build container with SSH server
- Start container with port forwarding
- Establish tunnel
- Send URL through wrapper script
- Verify host receives and processes it

### Step 9: Documentation

**File: `README.md`**

Add section:
- Browser Redirection: Explain how URLs open on host
  - How HTTPS/HTTP URLs are forwarded
  - How `file://` URLs are translated from container to host paths
  - Path mapping explanation with examples
- Requirements: SSH server in container, port forwarding
- Troubleshooting:
  - Common SSH/tunnel issues
  - URLs not opening (check path mappings)
  - file:// URLs opening wrong location (path mapping misconfiguration)

**File: `CLAUDE.md`**

Update:
- Document `browser_bridge.py` module
  - `BrowserBridge` class with path mapping functionality
  - `_translate_url()` method for file:// path conversion
- Document SSH key management in `container.py`
- Add testing requirements for browser bridge
  - Include URL translation test coverage requirements

## Implementation Order

1. ✓ Create this plan (spec/002-browser.md)
2. ✓ Add SSH server configuration to Dockerfile template
3. ✓ Implement SSH key management (`container.py`, `config.py`)
4. ✓ Create browser wrapper script template
5. ✓ Implement `BrowserBridge` class (`browser_bridge.py`)
6. ✓ Update `ContainerManager` for port forwarding and reverse tunnel
7. ✓ Integrate into main flow (setup/claude commands)
8. ✓ Add error handling and logging (custom exceptions, graceful degradation)
9. ✓ Write unit tests (131 tests covering all components)
10. Write integration tests
11. Update documentation
12. Test end-to-end with real container

## Open Questions

1. **Container IP discovery**: Does macOS `container` tool provide inspection/IP lookup?
   - Resolution: Use port forwarding approach instead (simpler)

2. **SSH daemon startup time**: How long to wait before connecting?
   - Resolution: Implement retry logic with exponential backoff

3. **Multiple concurrent containers**: How to handle port conflicts?
   - Resolution: Dynamic port allocation or use container name/ID in port number

4. **Graceful degradation**: What if SSH setup fails?
   - Resolution: Log warning, continue without browser bridge (URLs just fail silently)

5. **Security**: Exposing SSH port even on localhost?
   - Resolution: Only bind to 127.0.0.1, use key-only auth, close after session

## Dependencies

- No new Python dependencies (uses stdlib: `socket`, `subprocess`, `threading`)
- Container must have: `openssh-server`, `netcat`
- Host must have: SSH client (built into macOS)

## Success Criteria

- [ ] Container can be built with SSH server
- [ ] Host can establish reverse tunnel to container
- [ ] URLs sent in container appear in host browser
- [ ] All tests pass with >95% coverage
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
