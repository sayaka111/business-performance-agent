"""Presence of a real key alone must never enable live network calls."""

import os
import subprocess
import sys
import unittest


class LiveIsolationTests(unittest.TestCase):
    def test_key_without_opt_in_skips_before_client_creation(self):
        script = """
import unittest
from unittest.mock import patch
from tests.test_gemini_live import GeminiLiveTests
with patch('business_performance_agent.llm.gemini_client.GeminiLLMClient.__init__', side_effect=AssertionError('Network client must not be created')):
    result = unittest.TestResult()
    unittest.defaultTestLoader.loadTestsFromTestCase(GeminiLiveTests).run(result)
    assert len(result.skipped) == 1 and not result.errors and not result.failures
"""
        env = dict(os.environ, GEMINI_API_KEY="offline-placeholder")
        env.pop("BPA_RUN_LIVE_TESTS", None)
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_discovery_skips_even_when_opted_in(self):
        script = """
import unittest
from unittest.mock import patch
with patch('business_performance_agent.llm.gemini_client.GeminiLLMClient.__init__', side_effect=AssertionError('Discovery must stay offline')):
    result = unittest.TestResult()
    unittest.defaultTestLoader.discover('tests', pattern='test_gemini_live.py').run(result)
    assert len(result.skipped) == 1 and not result.errors and not result.failures
"""
        env = dict(
            os.environ, GEMINI_API_KEY="offline-placeholder", BPA_RUN_LIVE_TESTS="1"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
