"""Tests for SSRF protection — validate_outbound_url()."""

import socket
from unittest.mock import patch

import pytest

from app.security.ssrf import validate_outbound_url


class TestSchemeValidation:
    def test_https_allowed(self):
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("1.2.3.4", 0))]
            validate_outbound_url("https://api.github.com/repos/org/repo/pulls/1/files")

    def test_http_allowed(self):
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("1.2.3.4", 0))]
            validate_outbound_url("http://api.github.com/test")

    def test_ftp_rejected(self):
        with pytest.raises(ValueError, match="disallowed scheme"):
            validate_outbound_url("ftp://api.github.com/file")

    def test_file_scheme_rejected(self):
        with pytest.raises(ValueError, match="disallowed scheme"):
            validate_outbound_url("file:///etc/passwd")


class TestHostAllowlist:
    def test_github_api_allowed(self):
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("140.82.114.6", 0))]
            validate_outbound_url("https://api.github.com/repos/org/repo/pulls/1/files")

    def test_gitlab_allowed(self):
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("172.65.251.78", 0))]
            validate_outbound_url(
                "https://gitlab.com/api/v4/projects/1/merge_requests/1/changes"
            )

    def test_bitbucket_allowed(self):
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("104.192.143.1", 0))]
            validate_outbound_url(
                "https://api.bitbucket.org/2.0/repositories/org/repo/pullrequests/1"
            )

    def test_internal_host_rejected(self):
        with pytest.raises(ValueError, match="not in allowlist"):
            validate_outbound_url("https://internal-service.company.com/api/data")

    def test_attacker_host_rejected(self):
        with pytest.raises(ValueError, match="not in allowlist"):
            validate_outbound_url("https://evil.com/steal-token")

    def test_custom_allowed_host_via_env(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_DIFF_HOSTS", "selfhosted.gitlab.example.com")
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("203.0.113.1", 0))]
            validate_outbound_url(
                "https://selfhosted.gitlab.example.com/api/v4/projects/1/mr/1"
            )


class TestPrivateIPBlocking:
    def _run_with_ip(self, ip: str) -> None:
        with patch("app.security.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, (ip, 0))]
            validate_outbound_url("https://api.github.com/test")

    def test_loopback_ipv4_blocked(self):
        with pytest.raises(ValueError, match="private/reserved"):
            self._run_with_ip("127.0.0.1")

    def test_loopback_ipv6_blocked(self):
        with pytest.raises(ValueError, match="private/reserved"):
            self._run_with_ip("::1")

    def test_rfc1918_10_blocked(self):
        with pytest.raises(ValueError, match="private/reserved"):
            self._run_with_ip("10.0.0.1")

    def test_rfc1918_172_blocked(self):
        with pytest.raises(ValueError, match="private/reserved"):
            self._run_with_ip("172.16.0.1")

    def test_rfc1918_192_blocked(self):
        with pytest.raises(ValueError, match="private/reserved"):
            self._run_with_ip("192.168.1.1")

    def test_link_local_blocked(self):
        with pytest.raises(ValueError, match="private/reserved"):
            self._run_with_ip("169.254.169.254")

    def test_public_ip_allowed(self):
        self._run_with_ip("140.82.114.6")

    def test_dns_failure_raises(self):
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            side_effect=socket.gaierror("NXDOMAIN"),
        ):
            with pytest.raises(ValueError, match="DNS resolution failed"):
                validate_outbound_url("https://api.github.com/test")


class TestMissingHostname:
    def test_no_hostname_rejected(self):
        with pytest.raises(ValueError):
            validate_outbound_url("https:///path/only")
