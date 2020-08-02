import gzip
import io
import json
import logging
from datetime import datetime, timezone
from typing import List


class CloudWatchLogsParser:
    log = logging.getLogger(__name__)

    def __init__(self):
        pass

    def parse_log_events(self, log_data: dict) -> List[dict]:
        bulk_payload = []
        log_group_name = (log_data["logGroup"].split("/")[-1]).lower()

        for event in log_data["logEvents"]:
            self.log.debug(f"Decoded: {event}")
            msg_str = event["message"]
            # delete bane of logs  since we already captured it as msg_str
            del event["message"]
            # for now we'll discard aws lambda usage logs
            if (
                msg_str.startswith("START Requ")
                or msg_str.startswith("END Requ")
                or msg_str.startswith("REPORT Requ")
            ):
                continue

            source = {}
            source["@timestamp"] = datetime.fromtimestamp(event["timestamp"] / 1000.0)
            source["@aws_account"] = (log_data["owner"]).lower()
            source["@log_group"] = (log_data["logGroup"]).lower()
            source["@log_stream"] = (log_data["logStream"]).lower()
            source["@payload"] = msg_str
            source.update(event)
            try:
                source.update(json.loads(msg_str))
            except Exception as ex:
                source.update(self.parse_dirty_json(msg_str))

            index_name = f"cw-{log_group_name}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
            index_name = index_name.replace(":", "").lower()

            action = {
                "_index": index_name,
                "_type": f"cw-logs-{log_group_name}",
                "_id": event["id"],
                "_source": source,
            }

            bulk_payload.append(action)

        self.log.debug("Inspect bulk payload")
        for p in bulk_payload:
            self.log.debug(json.dumps(p, indent=2, default=str))
        return bulk_payload

    def parse_dirty_json(self, dirty_json_str: str) -> dict:
        parsed_json = {}
        payload_str: str = dirty_json_str.replace("{", ", ").replace("}", ", ").replace("\n", "")
        payload_str = (
            payload_str.replace("\\", "").replace('"', "").replace("\\s", "").replace("\n", "")
        )
        self.log.debug(f"PAYLOAD STR: {payload_str}")
        pairs = payload_str.split(", ")

        for p in pairs:
            self.log.debug(f"PAIR: {p}")
            arr = p.split(": ")
            if len(arr) == 0 or len(arr) == 1 or arr[0] is None or len(arr[0]) == 0:
                self.log.debug(f"WILL DISCARD: {arr}")
                continue
            elif arr[0] == "timestamp":
                parsed_json["log_record_timestamp"] = arr[1]
                continue
            elif arr[0] == "message":  # don't key contents of payload
                break
            else:
                parsed_json[arr[0]] = arr[1]

        return parsed_json

    def gunzip_bytes_obj(self, bytes_obj):
        in_ = io.BytesIO()
        in_.write(bytes_obj)
        in_.seek(0)
        with gzip.GzipFile(fileobj=in_, mode="rb") as fo:
            gunzipped_bytes_obj = fo.read()
        return gunzipped_bytes_obj
