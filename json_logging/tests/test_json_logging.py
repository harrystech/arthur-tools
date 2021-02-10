import datetime
from unittest import TestCase

import json_logging


class JsonLoggingTests(TestCase):
    def test_simple_example(self):
        logger = json_logging.getLogger("example")
        logger.info("Hello", extra={"more": "stuff"})

    def test_date(self):
        logger = json_logging.getLogger("example")
        today = datetime.datetime(2021, 2, 10, 21, 15, 35, 422060)
        logger.info(f"Today is {today}", extra={"today": datetime.datetime(2021, 2, 10, 21, 15)})
