import datetime
import json
from unittest import TestCase

import json_logging


class JsonLoggingTests(TestCase):
    def setUp(self) -> None:
        json_logging.configure_logging()
        self.filter = json_logging.ContextFilter()
        self.formatter = json_logging.JsonFormatter()
        self.logger = json_logging.getLogger("unittest")

    def _setup_logger(self) -> None:
        # Within a context, the handler is replaced by a "capturing handler" from unittest.
        # So we must bring back our filter and formatter.
        for handler in self.logger.handlers:
            handler.addFilter(self.filter)
            handler.setFormatter(self.formatter)

    def test_keys(self) -> None:
        """Checking whether keys are present."""
        with self.assertLogs(self.logger) as cm:
            self._setup_logger()
            self.logger.info("Hello World")
        parsed = json.loads(cm.output[0])

        # Just testing the most basic keys for now.
        for key in ["elapsed_ms", "gmtime", "log_level", "message", "timestamp"]:
            with self.subTest(key=key):
                self.assertIn(key, parsed)
                self.assertIsNotNone(parsed[key])

    def test_passing_extras(self) -> None:
        """Checking whether we can pass extra dict."""
        with self.assertLogs(self.logger) as cm:
            self._setup_logger()
            self.logger.info("Saving metrics", extra={"metrics": {"count": 1}})
        parsed = json.loads(cm.output[0])

        self.assertIn("metrics", parsed)
        self.assertDictEqual(parsed["metrics"], {"count": 1})

    def test_request_id(self) -> None:
        """Checking whether we can set a request id."""
        with self.assertLogs(self.logger) as cm:
            self._setup_logger()
            json_logging.update_context(request_id="test-123")
            self.logger.info("test request_id")
        parsed = json.loads(cm.output[0])

        self.assertIn("request_id", parsed)
        self.assertEqual(parsed["request_id"], "test-123")

    def test_aware_datetime(self) -> None:
        """Checking whether datetime (with timezone) is correctly formatted."""
        sometime = datetime.datetime(
            year=2021, month=3, day=14, hour=15, minute=9, tzinfo=datetime.timezone.utc
        )
        with self.assertLogs(self.logger) as cm:
            self._setup_logger()
            self.logger.info("Adding aware date", extra={"pi_day": sometime})
        parsed = json.loads(cm.output[0])

        self.assertIn("pi_day", parsed)
        # Apologies for the extra 0s.
        self.assertEqual(parsed["pi_day"], "2021-03-14T15:09:00.000Z")
