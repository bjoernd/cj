"""Tests for browser_bridge module."""

import socket
import time
from unittest.mock import patch
from cjlib.browser_bridge import BrowserBridge


class TestBrowserBridge:
    """Tests for BrowserBridge class."""

    def test_init_with_defaults(self):
        """Test BrowserBridge initialization with default parameters."""
        bridge = BrowserBridge()

        assert bridge.port == 9999
        assert bridge.path_mappings == []
        assert bridge.running is False

    def test_init_with_custom_port(self):
        """Test BrowserBridge initialization with custom port."""
        bridge = BrowserBridge(port=8888)

        assert bridge.port == 8888

    def test_init_with_path_mappings(self):
        """Test BrowserBridge initialization with path mappings."""
        mappings = [("/root/project", "/Users/test/project")]
        bridge = BrowserBridge(path_mappings=mappings)

        assert bridge.path_mappings == mappings

    def test_translate_http_url_unchanged(self):
        """Test that HTTP URLs pass through unchanged."""
        bridge = BrowserBridge()
        url = "http://example.com/page.html"

        result = bridge._translate_url(url)

        assert result == url

    def test_translate_https_url_unchanged(self):
        """Test that HTTPS URLs pass through unchanged."""
        bridge = BrowserBridge()
        url = "https://example.com/page.html"

        result = bridge._translate_url(url)

        assert result == url

    def test_translate_file_url_with_mapping(self):
        """Test file:// URL translation with matching mapping."""
        mappings = [("/root/project", "/Users/test/project")]
        bridge = BrowserBridge(path_mappings=mappings)
        url = "file:///root/project/output.html"

        result = bridge._translate_url(url)

        assert result == "file:///Users/test/project/output.html"

    def test_translate_file_url_with_multiple_mappings(self):
        """Test file:// URL translation with multiple mappings."""
        mappings = [
            ("/root/project", "/Users/test/project"),
            ("/root/.claude", "/Users/test/.cj/claude"),
        ]
        bridge = BrowserBridge(path_mappings=mappings)
        url = "file:///root/.claude/logs/debug.html"

        result = bridge._translate_url(url)

        assert result == "file:///Users/test/.cj/claude/logs/debug.html"

    def test_translate_file_url_first_matching_mapping_wins(self):
        """Test that first matching mapping is used."""
        mappings = [
            ("/root", "/Users/test1"),
            ("/root/project", "/Users/test2"),
        ]
        bridge = BrowserBridge(path_mappings=mappings)
        url = "file:///root/project/file.html"

        result = bridge._translate_url(url)

        # First mapping should match
        assert result == "file:///Users/test1/project/file.html"

    @patch("logging.warning")
    def test_translate_file_url_no_mapping_logs_warning(self, mock_warning):
        """Test that unmapped file:// URLs log a warning."""
        bridge = BrowserBridge(path_mappings=[])
        url = "file:///tmp/report.html"

        result = bridge._translate_url(url)

        assert result == url
        mock_warning.assert_called_once()
        assert "No path mapping found" in str(mock_warning.call_args)

    def test_translate_file_url_partial_match_not_translated(self):
        """Test that partial path matches don't translate."""
        mappings = [("/root/project", "/Users/test/project")]
        bridge = BrowserBridge(path_mappings=mappings)
        url = "file:///root/other/file.html"

        with patch("logging.warning"):
            result = bridge._translate_url(url)

        assert result == url

    @patch("subprocess.run")
    def test_open_url_calls_open_command(self, mock_run):
        """Test that _open_url calls the open command."""
        bridge = BrowserBridge()
        url = "https://example.com"

        bridge._open_url(url)

        mock_run.assert_called_once_with(["open", url], check=False, capture_output=True)

    @patch("subprocess.run")
    @patch("logging.error")
    def test_open_url_handles_exceptions(self, mock_error, mock_run):
        """Test that _open_url handles exceptions gracefully."""
        bridge = BrowserBridge()
        mock_run.side_effect = Exception("Command failed")

        bridge._open_url("https://example.com")

        mock_error.assert_called_once()

    def test_start_sets_running_flag(self):
        """Test that start() sets the running flag."""
        bridge = BrowserBridge()

        bridge.start()
        time.sleep(0.1)  # Give thread time to start

        assert bridge.running is True

        bridge.stop()

    def test_start_idempotent(self):
        """Test that calling start() multiple times is safe."""
        bridge = BrowserBridge()

        bridge.start()
        bridge.start()

        assert bridge.running is True

        bridge.stop()

    def test_stop_clears_running_flag(self):
        """Test that stop() clears the running flag."""
        bridge = BrowserBridge()

        bridge.start()
        time.sleep(0.1)
        bridge.stop()

        assert bridge.running is False

    def test_stop_idempotent(self):
        """Test that calling stop() multiple times is safe."""
        bridge = BrowserBridge()

        bridge.start()
        time.sleep(0.1)
        bridge.stop()
        bridge.stop()

        assert bridge.running is False

    @patch("subprocess.run")
    def test_receives_url_and_opens_it(self, mock_run):
        """Test that bridge receives URL via socket and opens it."""
        bridge = BrowserBridge(port=19999)  # Use different port to avoid conflicts
        bridge.start()
        time.sleep(0.2)  # Give server time to start

        try:
            # Send URL to bridge
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("localhost", 19999))
            client.send(b"https://example.com\n")
            client.close()

            # Give bridge time to process
            time.sleep(0.2)

            # Verify open was called
            mock_run.assert_called_once_with(
                ["open", "https://example.com"], check=False, capture_output=True
            )
        finally:
            bridge.stop()

    @patch("subprocess.run")
    def test_translates_file_url_before_opening(self, mock_run):
        """Test that file:// URLs are translated before opening."""
        mappings = [("/root/project", "/Users/test/project")]
        bridge = BrowserBridge(port=19998, path_mappings=mappings)
        bridge.start()
        time.sleep(0.2)

        try:
            # Send file:// URL to bridge
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("localhost", 19998))
            client.send(b"file:///root/project/output.html\n")
            client.close()

            # Give bridge time to process
            time.sleep(0.2)

            # Verify translated URL was opened
            mock_run.assert_called_once_with(
                ["open", "file:///Users/test/project/output.html"],
                check=False,
                capture_output=True,
            )
        finally:
            bridge.stop()

    def test_handles_multiple_connections(self):
        """Test that bridge can handle multiple connections."""
        bridge = BrowserBridge(port=19997)
        bridge.start()
        time.sleep(0.2)

        try:
            with patch("subprocess.run") as mock_run:
                # Send multiple URLs
                for i in range(3):
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("localhost", 19997))
                    client.send(f"https://example{i}.com\n".encode())
                    client.close()
                    time.sleep(0.1)

                # Give bridge time to process all
                time.sleep(0.2)

                # Verify all were opened
                assert mock_run.call_count == 3
        finally:
            bridge.stop()
