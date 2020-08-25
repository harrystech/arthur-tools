from unittest import TestCase

import json_logging


class JsonLoggingTests(TestCase):
    def test_simple_example(self):
        logger = json_logging.getLogger("example")
        logger.info("Hello", extra={"more": "stuff"})
