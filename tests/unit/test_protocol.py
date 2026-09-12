"""
Unit tests for DriveByGesture Windows URL protocol handler and security validation.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from core.protocol import (
    MUTEX_NAME,
    PROTOCOL_NAME,
    REGISTRY_SUBKEY,
    get_expected_command,
    get_target_executable_path,
    is_url_protocol_registered,
    register_url_protocol,
    unregister_url_protocol,
    validate_protocol_url,
)


class TestProtocolValidation(unittest.TestCase):
    """Test strict security validation of incoming protocol URLs."""

    def test_valid_launch_urls(self):
        valid_urls = [
            "rageware-gesture-drive://launch",
            "rageware-gesture-drive://launch/",
            "rageware-gesture-drive:launch",
            "RAGEWARE-GESTURE-DRIVE://LAUNCH",
            "rageware-gesture-drive:///launch",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(validate_protocol_url(url), f"Should accept: {url}")

    def test_invalid_scheme_rejected(self):
        invalid_schemes = [
            "http://launch",
            "https://launch",
            "other-protocol://launch",
            "file:///launch",
        ]
        for url in invalid_schemes:
            with self.subTest(url=url):
                self.assertFalse(validate_protocol_url(url), f"Should reject invalid scheme: {url}")

    def test_invalid_action_rejected(self):
        invalid_actions = [
            "rageware-gesture-drive://something.exe",
            "rageware-gesture-drive://cmd.exe",
            "rageware-gesture-drive://powershell",
            "rageware-gesture-drive://exit",
            "rageware-gesture-drive://shutdown",
            "rageware-gesture-drive://launch/extra_path",
        ]
        for url in invalid_actions:
            with self.subTest(url=url):
                self.assertFalse(validate_protocol_url(url), f"Should reject unauthorized action: {url}")

    def test_query_and_fragment_rejected(self):
        dangerous_urls = [
            "rageware-gesture-drive://launch?exec=calc.exe",
            "rageware-gesture-drive://launch?arg=--dangerous",
            "rageware-gesture-drive://launch#fragment",
        ]
        for url in dangerous_urls:
            with self.subTest(url=url):
                self.assertFalse(validate_protocol_url(url), f"Should reject URL with params: {url}")

    def test_malformed_and_empty_rejected(self):
        malformed = [
            "",
            None,
            "not a url",
            "rageware-gesture-drive",
            "://launch",
        ]
        for item in malformed:
            with self.subTest(item=item):
                self.assertFalse(validate_protocol_url(item))


class TestPathAndCommandConstruction(unittest.TestCase):
    """Test dynamic target path resolution and registry command formatting."""

    def test_target_executable_path_resolution(self):
        target = get_target_executable_path()
        self.assertIsInstance(target, Path)
        self.assertTrue(target.is_absolute())

    def test_frozen_target_path(self):
        dummy_exe = r"C:\Program Files\DriveByGesture\DriveByGesture.exe"
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "executable", dummy_exe
        ):
            target = get_target_executable_path()
            self.assertEqual(target, Path(dummy_exe))

    def test_command_quoting_with_spaces(self):
        path_with_spaces = Path(r"C:\Custom Apps\Drive By Gesture\DriveByGesture.exe")
        cmd = get_expected_command(path_with_spaces)
        self.assertEqual(cmd, f'"{path_with_spaces}" "%1"')


@unittest.skipUnless(sys.platform == "win32", "Windows registry tests only run on win32")
class TestRegistryRegistrationWindows(unittest.TestCase):
    """Test registry operations in HKCU (per-user, non-elevated)."""

    def test_registration_and_unregistration_cycle(self):
        # 1. Register with current target
        target = get_target_executable_path()
        reg_ok = register_url_protocol(target)
        self.assertTrue(reg_ok, "Protocol registration in HKCU should succeed")

        # 2. Check registered state
        self.assertTrue(
            is_url_protocol_registered(get_expected_command(target)),
            "Protocol should report as registered",
        )

        # 3. Idempotent call should succeed without error
        self.assertTrue(register_url_protocol(target), "Subsequent registration should succeed")

        # 4. Unregister
        unreg_ok = unregister_url_protocol()
        self.assertTrue(unreg_ok, "Protocol unregistration from HKCU should succeed")

        # 5. Check unmounted
        self.assertFalse(
            is_url_protocol_registered(get_expected_command(target)),
            "Protocol should no longer report as registered after unregistration",
        )

        # 6. Re-register so environment stays configured
        register_url_protocol(target)


if __name__ == "__main__":
    unittest.main()
