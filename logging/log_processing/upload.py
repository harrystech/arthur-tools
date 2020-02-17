"""
Uploader and Lambda handler -- send log records to Elasticsearch service.

From the command line, pick local files or files in S3, parse their content, and send
log records to ES domain.

As a lambda handler, extract the new file in S3 from the event information,
parse that file and send it to ES domain.
"""

import itertools
import sys
import urllib.parse

import botocore.exceptions
import elasticsearch
import elasticsearch.helpers

from log_processing import compile, config, json_logging, parse

# This is done during module initialization so that it is done once for a Lambda runtime environment.
json_logging.configure_logging()
logger = json_logging.getLogger(__name__)


def _build_actions_from(index, records):
    for record in records:
        yield {
            "_op_type": "index",
            "_index": index,
            "_id": record.id_,
            "_source": record.data,
        }


def index_records(es, records_generator):
    """
    Bulk-index log records. The appropriate index is chosen given the date of the log record.
    """
    for date, records in itertools.groupby(records_generator, key=lambda rec: rec["datetime"]["date"]):
        index = config.get_index_name(date)
        n_errors = 0
        n_ok, errors = elasticsearch.helpers.bulk(es, _build_actions_from(index, records))
        if errors:
            logger.warning(f"Index errors: {errors}")
            n_errors = len(errors)
        logger.info(f"Indexed successfully={n_ok:d}, unsuccessfully={n_errors:d}, index={index}")


def lambda_handler(event, context):
    """
    Callback handler for Lambda.

    Expected event structure:
    {
        "Records": [
            {
                "eventTime": "1970-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": { "name": "source_bucket" },
                    "object": { "key": "StdError.gz" }
                }
            }
        ]
    }
    """
    json_logging.update_context(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name,
        function_version=context.function_version,
        log_stream_name=context.log_stream_name,
    )
    for i, event_data in enumerate(event["Records"]):
        logger.info(
            "Event #{i}: source={eventSource}, name={eventName}, time={eventTime}".format(i=i, **event_data),
            extra={"event_source": event_data["eventSource"], "event_name": event_data["eventName"]},
        )
        bucket_name = event_data["s3"]["bucket"]["name"]
        object_key = urllib.parse.unquote_plus(event_data["s3"]["object"]["key"])
        is_log_file = object_key.startswith("_logs/") or "/logs/" in object_key
        logger.info(f"Bucket={bucket_name}, object={object_key}, is_log_file={is_log_file}")
        if not is_log_file:
            continue

        file_uri = "s3://{}/{}".format(bucket_name, object_key)
        processed = compile.load_records([file_uri])

        try:
            host, port = config.get_es_endpoint(bucket_name=bucket_name)
            es = config.connect_to_es(host, port, use_auth=True)
            if not config.exists_index_template(es):
                config.put_index_template(es)
        except botocore.exceptions.ClientError as exc:
            logger.warning(f"Failed in initial connection: {exc!s}")
            continue

        try:
            index_records(es, processed)
        except parse.NoRecordsFoundError:
            logger.info("Failed to find log records in object '{}'".format(file_uri))
            continue
        except botocore.exceptions.ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            logger.warning(f"Error code {error_code} for object '{file_uri}'")
            continue

        logger.info("Indexed log records successfully.", extra={"log_file_uri": file_uri})


def main():
    if len(sys.argv) < 3:
        print("Usage: {} env_type LOGFILE [LOGFILE ...]".format(sys.argv[0]))
        exit(1)
    env_type = sys.argv[1]
    processed = compile.load_records(sys.argv[2:])
    host, port = config.get_es_endpoint(env_type=env_type)
    es = config.connect_to_es(host, port)
    index_records(es, processed)


if __name__ == "__main__":
    main()
