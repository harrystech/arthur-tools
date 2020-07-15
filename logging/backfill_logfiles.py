#! /usr/bin/env python3

"""
Load log files into Elasticsearch domain.

This will only load files from stderr (which Arthur uses for its log output).
"""

import argparse
import base64
import json
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial

import boto3


def list_objects(bucket_name, prefix, days_in_past_limit):
    """
    Generate list of (object key, modified time) tuples from the bucket.

    The objects returned are limited to those with the prefix which have been modified
    no more than days_in_past_limit.
    """
    earliest = (datetime.utcnow() - timedelta(days=days_in_past_limit)).replace(tzinfo=timezone.utc)
    client = boto3.client("s3")
    paginator = client.get_paginator("list_objects_v2")
    response_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    logging.info("Looking for objects that may contain logs...")
    for response in response_iterator:
        for info in response["Contents"]:
            if info["LastModified"] > earliest:
                yield info["Key"], info["LastModified"]


def invoke_log_parser(function_name, bucket_name, object_key, event_time=datetime.utcnow().isoformat()):
    """
    Invoke the Lambda function specified by its name or ARN.

    The function will be invoked with an abbreviated S3 event that contains the
    bucket name and object key information.
    """
    logging.info("Invoking log parser for object=s3://{}/{}".format(bucket_name, object_key))
    payload = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "eventSource": "aws:s3",
                "eventTime": event_time.isoformat(),
                "s3": {"bucket": {"name": bucket_name}, "object": {"key": urllib.parse.quote_plus(object_key)}},
            }
        ]
    }
    payload_bytes = json.dumps(payload).encode()
    client = boto3.client("lambda")

    try:
        response = client.invoke(
            FunctionName=function_name, InvocationType="RequestResponse", LogType="Tail", Payload=payload_bytes,
        )
    except Exception:
        logging.exception("Invocation failed on object='s3://{}/{}':".format(bucket_name, object_key))
        raise
    logging.info("Tail of log:\n" + base64.standard_b64decode(response["LogResult"]).decode())

    status_code = response["StatusCode"]
    if status_code == 200:
        logging.info("Finished parsing of object='s3://{}/{}' successfully".format(bucket_name, object_key))
    else:
        logging.warning(
            "Finished parsing of object='s3://{}/{}' with status code {}".format(bucket_name, object_key, status_code)
        )


def main(bucket, prefix, function_name, days_in_past_limit, max_threads):
    logging.info("Attempting to load log files from bucket={} using function={}".format(bucket, function_name))
    logging.info("Arguments that limit objects: prefix={}, days_limit={}".format(prefix, days_in_past_limit))
    objects = list_objects(bucket, prefix, days_in_past_limit)
    object_keys = list(objects)  # list(map(itemgetter(0), sorted(objects, key=itemgetter(1), reverse=True)))
    logging.info("Found {} object(s) to process".format(len(object_keys)))

    threads = min(len(object_keys), max_threads)
    logging.info("Starting thread pool with {} thread(s)".format(threads))
    lambda_caller = partial(invoke_log_parser, function_name, bucket)
    with ThreadPoolExecutor(max_workers=threads, thread_name_prefix="lambda_caller") as executor:
        executor.map(lambda_caller, object_keys)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s (%(threadName)s) %(message)s")

    parser = argparse.ArgumentParser(
        description="Backfill Elasticsearch cluster using log files from the given bucket using the given lambda."
                    " (Tip: To load just one file, specify it as the prefix.)"
    )
    parser.add_argument(
        "prefix", help="Limit objects to those with the given prefix"
    )
    parser.add_argument(
        "--days-limit",
        type=int,
        default=365,
        metavar="N",
        help="Limit objects to those modified within the last N days (default: %(default)s)",
    )
    parser.add_argument("--threads", type=int, default=10, help="Number of threads to use")
    parser.add_argument("bucket", help="Name of bucket in S3")
    parser.add_argument("prefix", help="Limit objects to those with the given prefix")
    parser.add_argument("lambda_arn", help="ARN of Lambda that can process log files")
    args = parser.parse_args()

    main(args.bucket, args.prefix, args.lambda_arn, args.days_limit, args.threads)
