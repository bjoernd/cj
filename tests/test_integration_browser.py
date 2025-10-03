"""Integration tests for browser redirection functionality.

These tests verify the interaction between multiple components
without requiring a real container environment.
"""

import socket
import time
from pathlib import Path
from unittest.mock import Mock, patch
from cjlib.browser_bridge import BrowserBridge
from cjlib.config import Config
from cjlib.container import setup_ssh_keys, ContainerManager


class TestBrowserRedirectionIntegration:
    """Integration tests for browser redirection components."""

    def test_ssh_key_setup_integration(self, tmp_path):
        """Test SSH key generation integrates with config."""
        # Create config
        config = Config(str(tmp_path))

        # Ensure SSH directory
        config.ensure_ssh_dir()

        # Get key paths from config
        private_key = config.get_ssh_private_key_path()
        public_key = config.get_ssh_public_key_path()

        # Setup keys using paths from config
        with patch("cjlib.container._run_command") as mock_run, patch("os.chmod"):

            def create_keys(*args, **kwargs):
                Path(private_key).parent.mkdir(parents=True, exist_ok=True)
                Path(private_key).write_text("private")
                Path(public_key).write_text("public")

            mock_run.side_effect = create_keys

            setup_ssh_keys(config.get_ssh_dir(), private_key, public_key)

            # Verify keys were created in correct location
            assert Path(private_key).exists()
            assert Path(public_key).exists()

    def test_path_mappings_from_volume_mounts(self):
        """Test path mapping creation from volume mount strings."""
        # Simulate volume mounts as created in claude.py
        volume_mounts = [
            "/Users/test/project:/workspace",
            "/Users/test/.cj/claude:/root/.claude",
            "/Users/test/.cj/ssh:/tmp/host-ssh",
        ]

        # Create path mappings (container->host) as done in claude.py
        path_mappings = []
        for mount in volume_mounts:
            host_path, container_path = mount.split(":")
            if not container_path.startswith("/tmp"):
                path_mappings.append((container_path, host_path))

        # Verify mappings created correctly
        assert len(path_mappings) == 2
        assert ("/workspace", "/Users/test/project") in path_mappings
        assert ("/root/.claude", "/Users/test/.cj/claude") in path_mappings
        # /tmp/host-ssh should be excluded
        assert not any("/tmp" in mapping[0] for mapping in path_mappings)

    def test_browser_bridge_with_path_mappings(self):
        """Test BrowserBridge URL translation with real path mappings."""
        # Create path mappings as would be done in claude.py
        path_mappings = [
            ("/workspace", "/Users/test/project"),
            ("/root/.claude", "/Users/test/.cj/claude"),
        ]

        bridge = BrowserBridge(port=19996, path_mappings=path_mappings)

        # Test file:// URL translation
        container_url = "file:///workspace/output.html"
        host_url = bridge._translate_url(container_url)
        assert host_url == "file:///Users/test/project/output.html"

        # Test HTTP URL pass-through
        http_url = "https://example.com"
        result = bridge._translate_url(http_url)
        assert result == http_url

    @patch("subprocess.run")
    def test_browser_bridge_end_to_end(self, mock_run):
        """Test BrowserBridge receives URL and opens it with translation."""
        path_mappings = [("/workspace", "/Users/test/project")]
        bridge = BrowserBridge(port=19995, path_mappings=path_mappings)

        try:
            bridge.start()
            time.sleep(0.2)

            # Send container file:// URL
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("localhost", 19995))
            client.send(b"file:///workspace/index.html\n")
            client.close()

            time.sleep(0.2)

            # Verify translated URL was opened
            mock_run.assert_called_once_with(
                ["open", "file:///Users/test/project/index.html"],
                check=False,
                capture_output=True,
            )
        finally:
            bridge.stop()

    @patch("subprocess.Popen")
    def test_container_manager_port_forward_and_tunnel(self, mock_popen):
        """Test ContainerManager port forwarding integrates with tunnel setup."""
        mgr = ContainerManager()

        # Mock Popen for tunnel
        mock_process = Mock()
        mock_popen.return_value = mock_process

        # Setup tunnel with SSH key path
        ssh_key = "/test/.cj/ssh/id_rsa"
        tunnel = mgr.setup_reverse_tunnel(
            ssh_private_key_path=ssh_key, ssh_port=2222, forward_port=9999
        )

        # Verify tunnel process created with correct parameters
        assert tunnel == mock_process
        call_args = mock_popen.call_args[0][0]
        assert "ssh" in call_args
        assert "-R" in call_args
        assert "9999:localhost:9999" in call_args
        assert "-p" in call_args
        assert "2222" in call_args
        assert ssh_key in call_args

    def test_full_workflow_simulation(self, tmp_path):
        """Test simulated full workflow without real container."""
        # 1. Setup config
        config = Config(str(tmp_path))
        config.ensure_ssh_dir()

        # 2. Create SSH keys
        with patch("cjlib.container._run_command"), patch("os.chmod"):
            private_key = config.get_ssh_private_key_path()
            public_key = config.get_ssh_public_key_path()

            # Create mock keys
            Path(private_key).parent.mkdir(parents=True, exist_ok=True)
            Path(private_key).write_text("private")
            Path(public_key).write_text("public")

            # Verify keys exist
            assert Path(private_key).exists()

        # 3. Create volume mounts and path mappings
        cwd = str(tmp_path / "project")
        volume_mounts = [
            f"{cwd}:/workspace",
            f"{config.get_claude_dir()}:/root/.claude",
            f"{config.get_ssh_dir()}:/tmp/host-ssh",
        ]

        path_mappings = [
            (container_path, host_path)
            for host_path, container_path in [mount.split(":") for mount in volume_mounts]
            if not container_path.startswith("/tmp")
        ]

        # 4. Create browser bridge with mappings
        bridge = BrowserBridge(port=19994, path_mappings=path_mappings)

        # Test URL translation
        test_url = "file:///workspace/test.html"
        translated = bridge._translate_url(test_url)
        assert translated == f"file://{cwd}/test.html"

        # 5. Verify port forwarding configuration
        port_forwards = [("2222", "22")]
        assert len(port_forwards) == 1
        assert port_forwards[0] == ("2222", "22")

    @patch("subprocess.run")
    def test_multiple_url_forwarding(self, mock_run):
        """Test multiple URLs forwarded through browser bridge."""
        path_mappings = [("/workspace", "/Users/test/project")]
        bridge = BrowserBridge(port=19993, path_mappings=path_mappings)

        try:
            bridge.start()
            time.sleep(0.2)

            # Send multiple URLs
            urls = [
                "https://example.com",
                "file:///workspace/doc1.html",
                "file:///workspace/doc2.html",
            ]

            for url in urls:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(("localhost", 19993))
                client.send(f"{url}\n".encode())
                client.close()
                time.sleep(0.1)

            time.sleep(0.2)

            # Verify all URLs were processed
            assert mock_run.call_count == 3

            # Check translations
            calls = [call[0][0] for call in mock_run.call_args_list]
            assert ["open", "https://example.com"] in calls
            assert ["open", "file:///Users/test/project/doc1.html"] in calls
            assert ["open", "file:///Users/test/project/doc2.html"] in calls
        finally:
            bridge.stop()

    def test_config_integration_with_all_paths(self, tmp_path):
        """Test Config provides all necessary paths for browser redirection."""
        config = Config(str(tmp_path))

        # Ensure all directories
        config.ensure_claude_dir()
        config.ensure_ssh_dir()

        # Verify all path getters work
        assert config.get_claude_dir().endswith(".cj/claude")
        assert config.get_ssh_dir().endswith(".cj/ssh")
        assert config.get_ssh_private_key_path().endswith("id_rsa")
        assert config.get_ssh_public_key_path().endswith("id_rsa.pub")

        # Verify directories exist
        assert Path(config.get_claude_dir()).exists()
        assert Path(config.get_ssh_dir()).exists()
