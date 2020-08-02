import base64
import json
import logging
import os

from cw_logs_to_es.cw_log_parser import CloudWatchLogsParser
from cw_logs_to_es.es_helper import ElasticSearchWrapper
from harrys_logging import setup_logging

setup_logging(format_type="flat")
log: logging = logging.getLogger(__name__)

aws_es_helper = ElasticSearchWrapper(es_host=os.getenv("ES_HOST"), es_port=int(os.getenv("ES_PORT")))
cw_log_parser = CloudWatchLogsParser()


# TODO: define DLQ and alerts strategy
# TODO: tests!
# TODO: ci/cd
# TODO: cleanup parsing of dirty json
# TODO: acceptance criteria


def process(event, c):
    log.info(f"START")

    log_data_bytes = base64.b64decode(event["awslogs"]["data"])
    log_data_str = cw_log_parser.gunzip_bytes_obj(log_data_bytes)
    bulk_payload = cw_log_parser.parse_log_events(json.loads(log_data_str))
    aws_es_helper.insert_bulk_payload(bulk_payload)

    log.info(f"FINISH")
    return
