import json
import logging
from datetime import datetime
from typing import Iterator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CloudWatchLogsParser:
    def parse_log_events(self, log_data: dict) -> Iterator[dict]:
        shared = {
            "aws_account": log_data["owner"],
            "log_group": log_data["logGroup"],
            "log_stream": log_data["logStream"],
        }

        for event in log_data["logEvents"]:
            logger.debug(f"Parsing decoded log event id={event['id']}:\n{event}")

            timestamp = datetime.fromtimestamp(event["timestamp"] / 1000.0)
            index_name = f"cw-logs-{timestamp.strftime('%Y-%m')}"

            message = event["message"]
            if message.startswith(("START RequestId", "END RequestId")):
                continue
            if message.startswith("REPORT RequestId"):
                payload = self._parse_control_message(message)
            elif message.startswith("[ERROR] "):
                payload = self._parse_error_message(message)
            else:
                payload = self._parse_single_event(message)

            source = dict(shared)
            source.update(payload)
            source["@timestamp"] = timestamp

            # Build an action as required for bulk updates in ES.
            action = {
                "_id": event["id"],
                "_index": index_name,
                "_op_type": "index",
                "_source": source,
            }
            logger.debug(f"Adding action:\n{json.dumps(action, default=str)}")
            yield action

    @classmethod
    def _parse_control_message(cls, control: str) -> dict:
        clean_control = control.strip()
        fields = clean_control.split("\t")
        report = dict(message=clean_control, log_type="REPORT")
        for key, value in [field.split(":") for field in fields]:
            if key == "REPORT RequestId":
                report["aws_request_id"] = value.strip()
            elif key == "Duration":
                report["duration_in_ms"] = float(value[1:-3])
            elif key == "Billed Duration":
                report["billed_duration_in_ms"] = float(value[1:-3])
            elif key == "Memory Size":
                report["memory_size_in_mb"] = int(value[1:-3])
            elif key == "Max Memory Used":
                report["max_memory_used_in_mb"] = int(value[1:-3])
            elif key == "Init Duration":
                report["init_duration_in_ms"] = float(value[1:-3])
        return report

    @classmethod
    def _parse_error_message(cls, error_message: str) -> dict:
        error_report = {"log_type": "ERROR"}
        newline_pos = error_message.find("\n")
        if newline_pos < 0:
            error_report["message"] = error_message
        else:
            error_report["message"] = error_message[:newline_pos]
        return error_report

    @classmethod
    def _parse_single_event(cls, json_str: str) -> dict:
        try:
            return json.loads(json_str)
        except Exception as exc:
            # Parsing as JSON failed, try to recover by looking for pairs.
            recovered = cls._parse_dirty_json(json_str)
            if not recovered:
                # OK, this doesn't look like JSON at all.
                return dict(message=json_str, cwl_parser_exception=repr(exc))
            return dict(recovered, cwl_parser_exception=repr(exc))

    @classmethod
    def _parse_dirty_json(cls, dirty_json_str: str) -> dict:
        payload_str = (
            dirty_json_str.replace("{", ", ")
            .replace("}", ", ")
            .replace("\n", "")
            .replace("\\", "")
            .replace('"', "")
            .replace("\\s", "")
        )
        pairs = payload_str.split(", ")
        logger.debug(f"Recovered payload: {pairs}")

        parsed_json = {}
        for pair in pairs:
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
