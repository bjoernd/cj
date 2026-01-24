"""Tests for cjlib.proxy module."""

import socket
from unittest.mock import Mock, patch

import pytest

from cjlib.proxy import (
    ProxyManager,
    ProxyNotAvailableError,
    DEFAULT_ALLOWLIST,
)


class TestProxyManagerSquidChecks:
    """Tests for Squid availability checks."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_dir = "/tmp/test-cj"
        self.manager = ProxyManager(self.config_dir)

    @patch("shutil.which")
    def test_check_squid_installed_returns_true(self, mock_which):
        """Test that check_squid_installed returns True when squid is found."""
        mock_which.return_value = "/opt/homebrew/bin/squid"

        result = self.manager.check_squid_installed()

        assert result is True
        mock_which.assert_called_once_with("squid")

    @patch("shutil.which")
    def test_check_squid_installed_returns_false(self, mock_which):
        """Test that check_squid_installed returns False when squid is not found."""
        mock_which.return_value = None

        result = self.manager.check_squid_installed()

        assert result is False
        mock_which.assert_called_once_with("squid")

    @patch("socket.socket")
    def test_check_squid_running_returns_true(self, mock_socket_class):
        """Test that check_squid_running returns True when connection succeeds."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__ = Mock(return_value=mock_socket)
        mock_socket_class.return_value.__exit__ = Mock(return_value=False)
        mock_socket.connect.return_value = None

        result = self.manager.check_squid_running()

        assert result is True

    @patch("socket.socket")
    def test_check_squid_running_returns_false_on_connection_refused(self, mock_socket_class):
        """Test that check_squid_running returns False when connection fails."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__ = Mock(return_value=mock_socket)
        mock_socket_class.return_value.__exit__ = Mock(return_value=False)
        mock_socket.connect.side_effect = ConnectionRefusedError()

        result = self.manager.check_squid_running()

        assert result is False

    @patch("socket.socket")
    def test_check_squid_running_returns_false_on_timeout(self, mock_socket_class):
        """Test that check_squid_running returns False when connection times out."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__ = Mock(return_value=mock_socket)
        mock_socket_class.return_value.__exit__ = Mock(return_value=False)
        mock_socket.connect.side_effect = socket.timeout()

        result = self.manager.check_squid_running()

        assert result is False


class TestProxyManagerHostDetection:
    """Tests for host IP detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_dir = "/tmp/test-cj"
        self.manager = ProxyManager(self.config_dir)

    @patch("subprocess.run")
    def test_detect_host_ip_from_ipconfig(self, mock_run):
        """Test host IP detection using ipconfig getifaddr."""
        mock_run.return_value = Mock(returncode=0, stdout="192.168.1.100\n")

        result = self.manager.detect_host_ip()

        assert result == "192.168.1.100"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_detect_host_ip_fallback(self, mock_run):
        """Test host IP detection falls back to common gateway."""
        mock_run.return_value = Mock(returncode=1, stdout="")

        result = self.manager.detect_host_ip()

        assert result == "192.168.65.1"

    def test_get_proxy_url_with_auto_detection(self):
        """Test proxy URL generation with auto-detected host."""
        with patch.object(self.manager, "detect_host_ip", return_value="192.168.1.100"):
            result = self.manager.get_proxy_url()

        assert result == "http://192.168.1.100:3128"

    def test_get_proxy_url_with_host_override(self):
        """Test proxy URL generation with host override."""
        result = self.manager.get_proxy_url(host_override="10.0.0.1")

        assert result == "http://10.0.0.1:3128"


class TestProxyManagerAllowlist:
    """Tests for allowlist management."""

    def test_read_allowlist_returns_default_when_no_file(self, tmp_path):
        """Test read_allowlist returns default list when file doesn't exist."""
        manager = ProxyManager(str(tmp_path))

        result = manager.read_allowlist()

        assert result == DEFAULT_ALLOWLIST

    def test_write_and_read_allowlist(self, tmp_path):
        """Test write_allowlist and read_allowlist work together."""
        manager = ProxyManager(str(tmp_path))
        domains = ["example.com", ".example.org", "api.test.com"]

        manager.write_allowlist(domains)
        result = manager.read_allowlist()

        assert result == domains

    def test_read_allowlist_strips_empty_lines(self, tmp_path):
        """Test read_allowlist strips empty lines."""
        manager = ProxyManager(str(tmp_path))
        allowlist_file = tmp_path / "network-allowlist"
        allowlist_file.write_text("example.com\n\ntest.com\n\n")

        result = manager.read_allowlist()

        assert result == ["example.com", "test.com"]

    def test_merge_allowlist(self, tmp_path):
        """Test merge_allowlist combines and deduplicates domains."""
        manager = ProxyManager(str(tmp_path))
        manager.write_allowlist(["example.com", "test.com"])

        manager.merge_allowlist(["test.com", "new.com"])
        result = manager.read_allowlist()

        assert sorted(result) == ["example.com", "new.com", "test.com"]


class TestProxyManagerConfig:
    """Tests for Squid config generation."""

    def test_generate_squid_config(self, tmp_path):
        """Test Squid config generation."""
        manager = ProxyManager(str(tmp_path))
        manager.write_allowlist(["example.com", "test.com"])

        config = manager.generate_squid_config()

        assert "http_port 3128" in config
        assert "acl cj_allowed dstdomain" in config
        assert "http_access allow cj_allowed" in config
        assert "http_access deny all" in config

    def test_write_squid_config(self, tmp_path):
        """Test write_squid_config creates file."""
        manager = ProxyManager(str(tmp_path))
        manager.write_allowlist(["example.com"])

        manager.write_squid_config()

        squid_conf = tmp_path / "squid.conf"
        assert squid_conf.exists()
        content = squid_conf.read_text()
        assert "http_port 3128" in content

    def test_write_squid_config_creates_allowlist_if_missing(self, tmp_path):
        """Test write_squid_config creates allowlist with defaults if missing."""
        manager = ProxyManager(str(tmp_path))
        allowlist_path = tmp_path / "network-allowlist"
        assert not allowlist_path.exists()

        manager.write_squid_config()

        # Allowlist file should now exist with default domains
        assert allowlist_path.exists()
        content = allowlist_path.read_text()
        assert "api.anthropic.com" in content


class TestProxyManagerFilterEnabled:
    """Tests for network filter enabled state."""

    def test_is_filter_enabled_returns_false_when_no_file(self, tmp_path):
        """Test is_filter_enabled returns False when file doesn't exist."""
        manager = ProxyManager(str(tmp_path))

        result = manager.is_filter_enabled()

        assert result is False

    def test_set_filter_enabled_true(self, tmp_path):
        """Test set_filter_enabled(True) creates file with 'true'."""
        manager = ProxyManager(str(tmp_path))

        manager.set_filter_enabled(True)

        assert manager.is_filter_enabled() is True

    def test_set_filter_enabled_false(self, tmp_path):
        """Test set_filter_enabled(False) creates file with 'false'."""
        manager = ProxyManager(str(tmp_path))
        manager.set_filter_enabled(True)

        manager.set_filter_enabled(False)

        assert manager.is_filter_enabled() is False


class TestProxyManagerEnvVars:
    """Tests for proxy environment variables."""

    def test_get_proxy_env_vars(self, tmp_path):
        """Test get_proxy_env_vars returns all required variables."""
        manager = ProxyManager(str(tmp_path))

        with patch.object(manager, "get_proxy_url", return_value="http://192.168.1.100:3128"):
            result = manager.get_proxy_env_vars()

        assert "HTTP_PROXY=http://192.168.1.100:3128" in result
        assert "HTTPS_PROXY=http://192.168.1.100:3128" in result
        assert "http_proxy=http://192.168.1.100:3128" in result
        assert "https_proxy=http://192.168.1.100:3128" in result

    def test_get_proxy_env_vars_with_host_override(self, tmp_path):
        """Test get_proxy_env_vars with host override."""
        manager = ProxyManager(str(tmp_path))

        result = manager.get_proxy_env_vars(host_override="10.0.0.1")

        assert "HTTP_PROXY=http://10.0.0.1:3128" in result
        assert "HTTPS_PROXY=http://10.0.0.1:3128" in result


class TestProxyManagerSquidControl:
    """Tests for Squid process control."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_dir = "/tmp/test-cj"
        self.manager = ProxyManager(self.config_dir)

    @patch("subprocess.run")
    def test_reload_squid(self, mock_run):
        """Test reload_squid sends reconfigure signal."""
        mock_run.return_value = Mock(returncode=0)

        self.manager.reload_squid()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "squid" in call_args
        assert "-k" in call_args
        assert "reconfigure" in call_args

    @patch("subprocess.Popen")
    @patch.object(ProxyManager, "check_squid_running", side_effect=[False, True])
    def test_start_squid(self, mock_running, mock_popen, tmp_path):
        """Test start_squid starts Squid with our config."""
        manager = ProxyManager(str(tmp_path))
        manager.write_allowlist(["example.com"])
        manager.write_squid_config()

        manager.start_squid()

        mock_popen.assert_called_once()

    @patch("subprocess.run")
    def test_stop_squid(self, mock_run):
        """Test stop_squid sends shutdown signal."""
        mock_run.return_value = Mock(returncode=0)

        self.manager.stop_squid()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "squid" in call_args
        assert "-k" in call_args
        assert "shutdown" in call_args


class TestProxyManagerEnsureAvailable:
    """Tests for ensure_available method."""

    @patch.object(ProxyManager, "check_squid_installed", return_value=False)
    def test_ensure_available_raises_when_not_installed(self, mock_installed, tmp_path):
        """Test ensure_available raises when Squid is not installed."""
        manager = ProxyManager(str(tmp_path))

        with pytest.raises(ProxyNotAvailableError, match="Squid proxy is not installed"):
            manager.ensure_available()

    @patch.object(ProxyManager, "check_squid_installed", return_value=True)
    def test_ensure_available_succeeds_when_installed(self, mock_installed, tmp_path):
        """Test ensure_available succeeds when Squid is installed."""
        manager = ProxyManager(str(tmp_path))

        manager.ensure_available()


class TestDefaultAllowlist:
    """Tests for default allowlist domains."""

    def test_default_allowlist_contains_anthropic(self):
        """Test default allowlist contains Anthropic API."""
        assert "api.anthropic.com" in DEFAULT_ALLOWLIST

    def test_default_allowlist_contains_github(self):
        """Test default allowlist contains GitHub."""
        assert "github.com" in DEFAULT_ALLOWLIST
        assert ".github.com" in DEFAULT_ALLOWLIST

    def test_default_allowlist_contains_package_registries(self):
        """Test default allowlist contains package registries."""
        assert "registry.npmjs.org" in DEFAULT_ALLOWLIST
        assert "pypi.org" in DEFAULT_ALLOWLIST
        assert "files.pythonhosted.org" in DEFAULT_ALLOWLIST
        assert "crates.io" in DEFAULT_ALLOWLIST
        assert "static.crates.io" in DEFAULT_ALLOWLIST

    def test_default_allowlist_contains_rust(self):
        """Test default allowlist contains Rust installation domains."""
        assert "rustup.rs" in DEFAULT_ALLOWLIST
        assert "static.rust-lang.org" in DEFAULT_ALLOWLIST
