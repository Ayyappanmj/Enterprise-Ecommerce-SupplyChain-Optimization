import os
import tempfile
import unittest
from unittest.mock import patch

from src.utils.retry import retry_with_backoff
from src.etl import state_manager


class TestRetryWithBackoff(unittest.TestCase):
    def test_succeeds_after_transient_failures(self):
        calls = {"n": 0}

        @retry_with_backoff(max_attempts=5, base_delay=0.001)
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("transient")
            return "ok"

        result = flaky()
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)  # failed twice, succeeded on the 3rd attempt

    def test_raises_after_exhausting_attempts(self):
        calls = {"n": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0.001)
        def always_fails():
            calls["n"] += 1
            raise ConnectionError("permanent")

        with self.assertRaises(ConnectionError):
            always_fails()
        self.assertEqual(calls["n"], 3)  # tried exactly max_attempts times, not more/fewer

    def test_does_not_retry_on_non_matching_exception(self):
        calls = {"n": 0}

        @retry_with_backoff(max_attempts=5, base_delay=0.001, retry_on=(ConnectionError,))
        def wrong_error():
            calls["n"] += 1
            raise ValueError("not retryable")

        with self.assertRaises(ValueError):
            wrong_error()
        self.assertEqual(calls["n"], 1)  # no retry attempted for a non-matching exception type

    def test_succeeds_immediately_without_retry(self):
        calls = {"n": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0.001)
        def always_works():
            calls["n"] += 1
            return 42

        self.assertEqual(always_works(), 42)
        self.assertEqual(calls["n"], 1)


class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.state_file = os.path.join(self.tmpdir.name, "etl_state.json")
        self.patcher = patch.object(state_manager, "STATE_FILE", self.state_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()

    def test_default_watermark_when_no_state_file_exists(self):
        wm = state_manager.get_watermark("web_orders", default="1970-01-01")
        self.assertEqual(wm, "1970-01-01")

    def test_set_then_get_watermark_round_trips(self):
        state_manager.set_watermark("web_orders", "2024-06-15", rows_loaded=500)
        wm = state_manager.get_watermark("web_orders", default="1970-01-01")
        self.assertEqual(wm, "2024-06-15")

    def test_watermarks_are_independent_per_source(self):
        state_manager.set_watermark("web_orders", "2024-06-15", rows_loaded=10)
        state_manager.set_watermark("inventory", "2024-07-01", rows_loaded=20)
        self.assertEqual(state_manager.get_watermark("web_orders", "x"), "2024-06-15")
        self.assertEqual(state_manager.get_watermark("inventory", "x"), "2024-07-01")

    def test_state_file_is_valid_json_after_write(self):
        state_manager.set_watermark("shipping_api", "2024-01-01", rows_loaded=5)
        self.assertTrue(os.path.exists(self.state_file))
        full_state = state_manager.get_full_state()
        self.assertIn("shipping_api", full_state)
        self.assertEqual(full_state["shipping_api"]["rows_loaded_last_run"], 5)


if __name__ == "__main__":
    unittest.main()
