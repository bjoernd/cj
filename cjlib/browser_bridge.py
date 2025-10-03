"""Browser bridge module for forwarding URLs from container to host."""

import logging
import socket
import subprocess
import threading


class BrowserBridge:
    """Host-side URL listener that forwards URLs from container to host browser."""

    def __init__(self, port=9999, path_mappings=None):
        """Initialize browser bridge.

        Args:
            port: Port to listen on (default 9999)
            path_mappings: List of (container_path, host_path) tuples for file:// URL translation
        """
        self.port = port
        self.path_mappings = path_mappings or []
        self.running = False
        self._server_socket = None
        self._listener_thread = None

    def start(self):
        """Start listening for URLs in background thread."""
        if self.running:
            return

        self.running = True
        self._listener_thread = threading.Thread(target=self._listen, daemon=True)
        self._listener_thread.start()

    def stop(self):
        """Stop the listener."""
        if not self.running:
            return

        self.running = False

        # Close the server socket to unblock accept()
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

        # Wait for listener thread to finish
        if self._listener_thread:
            self._listener_thread.join(timeout=2.0)

    def _listen(self):
        """Main listener loop - receives URLs and opens them."""
        try:
            # Create and bind socket
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("localhost", self.port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)  # Timeout to check self.running

            while self.running:
                try:
                    # Accept incoming connection
                    client_socket, _ = self._server_socket.accept()

                    # Read URL from client
                    try:
                        data = client_socket.recv(4096)
                        if data:
                            url = data.decode("utf-8").strip()
                            if url:
                                # Translate and open URL
                                translated_url = self._translate_url(url)
                                self._open_url(translated_url)
                    finally:
                        client_socket.close()

                except socket.timeout:
                    # Timeout is expected, continue checking self.running
                    continue
                except OSError:
                    # Socket was closed, exit loop
                    if not self.running:
                        break
                    raise

        except Exception as e:
            if self.running:
                logging.error(f"Browser bridge listener error: {e}")
        finally:
            if self._server_socket:
                try:
                    self._server_socket.close()
                except Exception:
                    pass

    def _translate_url(self, url):
        """Translate file:// URLs from container paths to host paths.

        Args:
            url: URL to translate (may be file://, http://, https://, etc.)

        Returns:
            Translated URL (or original if no translation needed)
        """
        if not url.startswith("file://"):
            return url  # HTTP/HTTPS pass through unchanged

        # Extract path from file:// URL
        container_path = url[7:]  # Remove 'file://' prefix

        # Try each path mapping in order
        for container_prefix, host_prefix in self.path_mappings:
            if container_path.startswith(container_prefix):
                # Replace container prefix with host prefix
                host_path = container_path.replace(container_prefix, host_prefix, 1)
                return f"file://{host_path}"

        # No mapping found - log warning and return original
        # (will likely fail to open, but better than silent failure)
        logging.warning(f"No path mapping found for container path: {container_path}")
        return url

    def _open_url(self, url):
        """Open URL using the system's default handler.

        Args:
            url: URL to open
        """
        try:
            subprocess.run(["open", url], check=False, capture_output=True)
        except Exception as e:
            logging.error(f"Failed to open URL {url}: {e}")
