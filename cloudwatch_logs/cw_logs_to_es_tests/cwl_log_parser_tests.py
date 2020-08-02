import json
import logging
import sys
import warnings
from unittest import TestCase

from cw_logs_to_es_tests import TEST_ROOT_DIR
from harrys_logging import setup_logging

setup_logging(format_type="flat")


class CloudWatchLogsParserTests(TestCase):
    log = logging.getLogger(__name__)

    @classmethod
    def setUpClass(cls):
        if not sys.warnoptions:
            warnings.simplefilter("ignore")

        with open(f"{TEST_ROOT_DIR}/test_data/flat_aws_lambda_start_stop.json", "rb") as f:
            cls.flat_aws_lambda_start_stop = json.loads(f.read())

    def test_gunzip_bytes_obj(self):
        pass

    def test_parse_dirty_json_1(self):
        pass

    def test_parse_dirty_json_2(self):
        pass

    def parse_log_events_1(self):
        pass

    def parse_log_events_2(self):
        pass
