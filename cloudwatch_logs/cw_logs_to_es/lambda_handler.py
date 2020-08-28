import base64
import gzip
import json
import logging
import os
from typing import Any

from .cw_log_parser import CloudWatchLogsParser
from .es_helper import ElasticsearchWrapper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

es_domain_name = os.environ["ES_DOMAIN_NAME"]

es_wrapper = ElasticsearchWrapper(es_domain_name)
cw_log_parser = CloudWatchLogsParser()


def send_to_es(data: bytes) -> None:
    log_data_bytes = base64.b64decode(data)
    log_data_str = gzip.decompress(log_data_bytes)
    log_buffer = json.loads(log_data_str)
    bulk_payload = list(cw_log_parser.parse_log_events(log_buffer))
    es_wrapper.insert_bulk_payload(bulk_payload)


def process(event: Any, context: Any) -> None:
    logger.info("Starting to process event...")
    send_to_es(event["awslogs"]["data"])


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        send_to_es(sys.argv[1].encode("utf-8"))
    else:
        print(f"Usage: {sys.argv[0]} data")
