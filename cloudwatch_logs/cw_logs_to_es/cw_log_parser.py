import json
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CloudWatchLogsParser:
    def parse_log_events(self, log_data: dict) -> List[dict]:
        bulk_payload = []

        for event in log_data["logEvents"]:
            logger.debug(f"Decoded log event: {event}")

            # Move "message" body out of event structure.
            msg_str = event["message"]
            del event["message"]

            # Discard the AWS control messages
            if msg_str.startswith(("START RequestId", "END RequestId", "REPORT RequestId")):
                continue

            timestamp = datetime.fromtimestamp(event["timestamp"] / 1000.0)
            source = {
                "@timestamp": timestamp,
                "@aws_account": log_data["owner"].lower(),
                "@log_group": log_data["logGroup"].lower(),
                "@log_stream": log_data["logStream"].lower(),
                "@payload": msg_str,
            }
            index_name = f"cw-logs-{timestamp.strftime('%Y-%m')}"

            try:
                source.update(json.loads(msg_str))
            except Exception as exc:
                source["@json_exception"] = repr(exc)
                source.update(self.parse_dirty_json(msg_str))

            action = {
                "_id": event["id"],
                "_index": index_name,
                "_op_type": "index",
                "_source": source,
            }
            bulk_payload.append(action)

        logger.debug(f"Inspect bulk payload:\n{json.dumps(bulk_payload, default=str)}")
        return bulk_payload

    @staticmethod
    def parse_dirty_json(dirty_json_str: str) -> dict:
        payload_str = dirty_json_str.replace("{", ", ").replace("}", ", ").replace("\n", "")
        payload_str = (
            payload_str.replace("\\", "").replace('"', "").replace("\\s", "").replace("\n", "")
        )
        pairs = payload_str.split(", ")
        logger.debug(f"Recovered payload: {pairs}")

        parsed_json = {}
        for pair in payload_str.split(", "):
            arr = pair.split(": ")
            if len(arr) < 2 or not arr[0]:
                logger.debug(f"Discarding non-pair: {pair}")
            elif arr[0] == "timestamp":
                parsed_json["log_record_timestamp"] = arr[1]
            elif arr[0] == "message":  # don't key contents of payload
                break
            else:
                parsed_json[arr[0]] = arr[1]

        return parsed_json
